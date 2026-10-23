#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run unchanged, compiled local basu unit tests.
set -eu
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: run.sh ABSOLUTE_NEW_RESULTS [normal|valgrind]' >&2; exit 2; }
mode=${2:-normal}
case "$mode" in normal|valgrind) ;; *) echo 'Invalid test mode' >&2; exit 2 ;; esac
case "$1" in /*) ;; *) echo 'Absolute result path required' >&2; exit 2 ;; esac
[ ! -e "$1" ] && [ ! -L "$1" ] || { echo 'Results already exist' >&2; exit 2; }
[ "$(id -u)" != 0 ] || { echo 'Use an ordinary account' >&2; exit 2; }
PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/pkg/bin
export PATH
for program in timeout sha256 ldd; do command -v "$program" >/dev/null; done
if [ "$mode" = valgrind ]; then command -v valgrind >/dev/null; fi
bundle=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
umask 077
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd -P)
mkdir "$work/home" "$work/tmp" "$work/runtime" "$work/config" "$work/cache" "$work/data" "$work/state"
cd "$bundle"
while read -r expected file; do
    [ -f "$file" ] && [ "$(sha256 -q "$file")" = "$expected" ] || { echo "Bundle hash mismatch: $file" >&2; exit 1; }
done < SHA256SUMS
# Use the matching installed EmberBSD base. Do not ship or replace libc/rtld.
while read -r expected file; do
    [ -f "$file" ] && [ "$(sha256 -q "$file")" = "$expected" ] || { echo "Base hash mismatch: $file" >&2; exit 1; }
done < metadata/base.sha256
uname -a > "$work/system.txt"
id > "$work/user.txt"
/sbin/sysctl kern.boottime > "$work/boot.before"
child=
trap '[ -z "$child" ] || kill -TERM "$child" 2>/dev/null || :' 0
trap 'exit 130' INT
trap 'exit 143' TERM HUP
failed=0
for name in test-bus-signature test-bus-error test-bus-introspect; do
    binary="$bundle/bin/$name"
    env -i PATH="$PATH" LC_ALL=C LD_LIBRARY_PATH=/lib:/usr/lib \
        ldd "$binary" >> "$work/libraries.txt" 2>&1
    set -- "$binary"
    limit=30
    if [ "$mode" = valgrind ]; then
        set -- valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes \
            --errors-for-leak-kinds=definite,possible --error-exitcode=97 "$@"
        limit=300
    fi
    timeout -k 2 "$limit" env -i PATH="$PATH" LC_ALL=C HOME="$work/home" TMPDIR="$work/tmp" \
        XDG_RUNTIME_DIR="$work/runtime" XDG_CONFIG_HOME="$work/config" XDG_CACHE_HOME="$work/cache" \
        XDG_DATA_HOME="$work/data" XDG_STATE_HOME="$work/state" LD_LIBRARY_PATH=/lib:/usr/lib \
        DBUS_SESSION_BUS_ADDRESS="unix:path=$work/runtime/no-session-bus" \
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=$work/runtime/no-system-bus" \
        "$@" > "$work/$name.log" 2>&1 &
    child=$!
    result=0
    wait "$child" || result=$?
    child=
    printf '%s\t%s\n' "$name" "$result" >> "$work/status.tsv"
    [ "$result" = 0 ] || failed=1
done
/sbin/sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
[ "$failed" = 0 ] || { echo "FAIL: inspect $work/status.tsv" >&2; exit 1; }
printf 'PASS: three unchanged upstream basu local unit tests (%s)\n' "$mode"
