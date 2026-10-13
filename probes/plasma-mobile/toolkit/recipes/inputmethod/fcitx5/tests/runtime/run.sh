#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run original tests against installed libraries.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 PAYLOAD NEW_WORK" >&2; exit 2; }
payload=$1 work=$2
for item in "$@"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
[ "$(id -u)" != 0 ] || { echo 'Run as an ordinary user' >&2; exit 1; }
payload=$(cd "$payload" && pwd -P)
target_root=$(cat "$payload/provenance/target-root.txt")
[ "$payload" = "$target_root" ] || { echo "Extract payload at compiled fixture root: $target_root" >&2; exit 1; }
[ -w "$payload/build/test" ] || { echo 'Fixture build/test must be writable by this user' >&2; exit 1; }
hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    elif command -v sha256 >/dev/null 2>&1; then sha256 -q "$1"
    else shasum -a 256 "$1" | awk '{print $1}'
    fi
}
while IFS="$(printf '\t')" read -r expected item; do
    case "$item" in /*|../*|*/../*|*/..|..) echo 'Invalid manifest path' >&2; exit 1 ;; esac
    [ "$(hash_file "$payload/$item")" = "$expected" ] || {
        echo "Payload hash mismatch: $item" >&2; exit 1
    }
done < "$payload/SHA256.tsv"
for item in /usr/bin/timeout /usr/bin/ldd /usr/pkg/bin/fcitx5-remote; do
    [ -x "$item" ] || { echo "Missing installed tool: $item" >&2; exit 1; }
done
for item in libFcitx5Utils.so.2 libFcitx5Config.so.6 libFcitx5Core.so.7; do
    [ -f "/usr/pkg/lib/$item" ] || { echo "Missing installed library: $item" >&2; exit 1; }
done
[ ! -e "$work" ] && [ ! -L "$work" ]
umask 077
mkdir "$work"
work=$(cd "$work" && pwd -P)
mkdir "$work/logs" "$work/cases"
: > "$work/results.tsv"
pass=0 skip=0 fail=0
record() {
    case "$2" in
        0) result=PASS; pass=$((pass + 1)) ;;
        77) result=SKIP; skip=$((skip + 1)) ;;
        *) result=FAIL; fail=$((fail + 1)) ;;
    esac
    printf '%s\t%s\t%s\t%s\n' "$1" "$result" "$2" "$3" >> "$work/results.tsv"
    printf '%s: %s (exit %s) %s\n' "$1" "$result" "$2" "$3"
}
# Export only to child commands. Inherited display, session, and loader settings
# must not select another installation or a real desktop session.
child() {
    env -i PATH=/usr/pkg/bin:/usr/bin:/bin LC_ALL=C HOME="$task_home" \
        TMPDIR="$case_root/tmp" XDG_CONFIG_HOME="$case_root/config" \
        XDG_DATA_HOME="$case_root/data" XDG_CACHE_HOME="$case_root/cache" \
        XDG_RUNTIME_DIR="$case_root/runtime" \
        LD_LIBRARY_PATH=/usr/pkg/lib:/usr/pkg/gcc16/lib:/usr/pkg/lib/fcitx5 "$@"
}
while IFS="$(printf '\t')" read -r name mode; do
    case "$mode" in
        direct|dbus|remote|data|fixture) ;;
        *) echo "Unknown test mode: $mode" >&2; exit 1 ;;
    esac
    case_root=$work/cases/$name
    task_home=$case_root/home
    mkdir -p "$task_home" "$case_root/tmp" "$case_root/config" "$case_root/data" \
        "$case_root/cache" "$case_root/runtime"
    cd "$case_root"
    binary=$payload/build/bin/$name
    [ "$mode" != remote ] || binary=/usr/pkg/bin/fcitx5-remote
    status=0
    child /usr/bin/ldd "$binary" > "$work/logs/$name.ldd" 2>&1 || status=$?
    if [ "$status" != 0 ] || grep -F 'not found' "$work/logs/$name.ldd" >/dev/null; then
        record "$name" 1 'installed library resolution failed; see ldd log'
        continue
    fi
    if ! awk '/libFcitx5(Core|Config|Utils)[.]so/ {
            found = 1; if ($0 !~ /=> \/usr\/pkg\/lib\/libFcitx5/) bad = 1
        } END {exit (!found || bad)}' "$work/logs/$name.ldd"; then
        record "$name" 1 'Fcitx library did not resolve from installed prefix'
        continue
    fi
    case "$mode" in
        data)
            if ! grep -F '#define ISOCODES_ISO639_JSON "/usr/pkg/share/iso-codes/json/iso_639-3.json"' "$payload/provenance/config.h" >/dev/null ||
               ! grep -F '#define XKEYBOARDCONFIG_XKBBASE "/usr/pkg/share/X11/xkb"' "$payload/provenance/config.h" >/dev/null ||
               ! grep -F '#define XKEYBOARDCONFIG_DATADIR "/usr/pkg/share"' "$payload/provenance/config.h" >/dev/null; then
                record "$name" 1 'binary configuration embeds non-target data paths; rebuild required'
                continue
            fi
            if [ ! -s /usr/pkg/share/iso-codes/json/iso_639-3.json ] || [ ! -s /usr/pkg/share/X11/xkb/rules/evdev.xml ]; then
                record "$name" 1 'installed iso-codes or xkeyboard-config data missing'
                continue
            fi ;;
        dbus)
            if [ ! -x /usr/pkg/bin/dbus-daemon ]; then
                record "$name" 77 'installed dbus-daemon missing'
                continue
            fi ;;
    esac
    status=0
    case "$mode" in
        dbus) child /usr/bin/timeout -k 5 60 /bin/sh "$payload/source/test/dbus_wrapper.sh" \
            /usr/pkg/bin/dbus-daemon "$binary" > "$work/logs/$name.log" 2>&1 || status=$? ;;
        remote) child /usr/bin/timeout -k 5 60 env DBUS_SESSION_BUS_ADDRESS="unix:path=$case_root/nonexistent-dbus" \
            "$binary" --help > "$work/logs/$name.log" 2>&1 || status=$? ;;
        *) child /usr/bin/timeout -k 5 60 "$binary" > "$work/logs/$name.log" 2>&1 || status=$? ;;
    esac
    if [ "$status" = 0 ] && [ "$name" = testxkbrules ]; then
        # Upstream only prints this dump. Require real installed rule content.
        for expected in 'Layout Name: us' 'Layout Name: ru' 'Model Name: pc105' 'Option Group Name: grp'; do
            if ! grep -E "^[[:space:]]+$expected$" "$work/logs/$name.log" >/dev/null; then
                printf 'Missing expected XKB data: %s\n' "$expected" >> "$work/logs/$name.log"
                status=1
            fi
        done
    fi
    record "$name" "$status" 'original upstream case'
done < "$payload/cases.tsv"
printf 'SUMMARY: PASS=%s SKIP=%s FAIL=%s\n' "$pass" "$skip" "$fail"
[ "$fail" = 0 ]
