#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check installed Configtool entry points.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 NEW_RESULT_DIRECTORY" >&2; exit 2; }
[ "$(id -u)" != 0 ] || { echo 'Run as an ordinary user' >&2; exit 2; }
case "$1" in /*) ;; *) echo 'An absolute result directory is required' >&2; exit 2 ;; esac
umask 077
mkdir "$1"
out=$(cd "$1" && pwd -P)
mkdir "$out/home" "$out/config" "$out/cache" "$out/data" "$out/runtime"
for item in /usr/pkg/bin/dbus-run-session /usr/bin/timeout /usr/pkg/bin/kcmshell6; do
    [ -x "$item" ] || { echo "Missing executable: $item" >&2; exit 1; }
done
for item in /usr/pkg/bin/fcitx5-config-qt /usr/pkg/bin/fcitx5-migrator \
    /usr/pkg/bin/fcitx5-plasma-theme-generator /usr/pkg/bin/kbd-layout-viewer5 \
    /usr/pkg/lib/libFcitx5Migrator.so.1 \
    /usr/pkg/qt6/plugins/plasma/kcms/systemsettings/kcm_fcitx5.so; do
    [ -f "$item" ] || { echo "Missing installed file: $item" >&2; exit 1; }
    env -i PATH=/usr/bin:/bin /usr/bin/ldd "$item" >> "$out/ldd.log" 2>&1
    if grep -F 'not found' "$out/ldd.log" >/dev/null; then
        echo 'Installed library resolution failed' >&2; exit 1
    fi
done
run() {
    name=$1 expected=$2
    shift 2
    result=0
    env -i PATH=/usr/pkg/bin:/usr/bin:/bin LC_ALL=C HOME="$out/home" \
        XDG_CONFIG_HOME="$out/config" XDG_CACHE_HOME="$out/cache" \
        XDG_DATA_HOME="$out/data" XDG_RUNTIME_DIR="$out/runtime" \
        XDG_DATA_DIRS=/usr/pkg/share:/usr/share QT_QPA_PLATFORM=offscreen \
        QT_IM_MODULE=fcitx5 QT_PLUGIN_PATH=/usr/pkg/qt6/plugins \
        /usr/bin/timeout -k 5 30 /usr/pkg/bin/dbus-run-session -- "$@" \
        > "$out/$name.log" 2>&1 || result=$?
    printf '%s\t%s\n' "$name" "$result" >> "$out/status.tsv"
    [ "$result" = "$expected" ] || {
        echo "FAIL: $name returned $result, expected $expected" >&2; exit 1
    }
}
for app in fcitx5-config-qt fcitx5-migrator fcitx5-plasma-theme-generator; do
    run "$app-help" 0 "/usr/pkg/bin/$app" --help
    grep -F 'Usage:' "$out/$app-help.log"
    run "$app-version" 0 "/usr/pkg/bin/$app" --version
    grep -F -x "$app 5.1.16" "$out/$app-version.log"
done
run invalid-option 1 /usr/pkg/bin/fcitx5-config-qt --ember-invalid-option
grep -F "Unknown option 'ember-invalid-option'" "$out/invalid-option.log"
run kcm-discovery 0 /usr/pkg/bin/kcmshell6 --list
grep -E '^kcm_fcitx5[[:space:]]' "$out/kcm-discovery.log"
printf 'PASS: three help/version pairs, rejected option, installed KCM discovery\n'
printf 'Offscreen startup only. No settings change, migration, theme rendering or graphical input acceptance.\n'
printf 'kbd-layout-viewer5 requires X11; only its library resolution is checked here.\n'
