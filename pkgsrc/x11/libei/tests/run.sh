#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run the compiled upstream tests privately.
set -eu
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: run.sh NEW_RESULTS [normal|valgrind]' >&2; exit 2; }
mode=${2:-normal}
case "$mode" in normal|valgrind) ;; *) exit 2;; esac
bundle=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$1" in /*) ;; *) echo 'Use an absolute result directory' >&2; exit 2;; esac
[ ! -e "$1" ] && [ ! -L "$1" ] || { echo 'Result directory exists' >&2; exit 2; }
PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/pkg/bin:/usr/pkg/sbin
export PATH
[ "$(id -u)" != 0 ] || { echo 'Run the tests as an ordinary user, not root' >&2; exit 2; }
for tool in timeout sha256 ldd; do command -v "$tool" >/dev/null;done
if [ "$mode" = valgrind ]; then command -v valgrind >/dev/null; fi
umask 077
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd -P)
mkdir "$work/home" "$work/tmp" "$work/runtime"
uname -a > "$work/kernel.txt"
(
    cd "$bundle"
    while read -r expected file; do
        [ "$(sha256 -q "$file")" = "$expected" ] || { echo "Hash mismatch: $file" >&2; exit 1; }
    done < SHA256SUMS
)
failed=0
run_test()
{
    name=$1
    shift
    result=0
    if [ "$mode" = valgrind ]; then
        set -- valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes \
            --errors-for-leak-kinds=definite,possible --error-exitcode=97 "$@"
        limit=300
    else
        limit=60
    fi
    timeout -k 5 "$limit" env -i PATH="$PATH" LC_ALL=C HOME="$work/home" \
        TMPDIR="$work/tmp" XDG_RUNTIME_DIR="$work/runtime" \
        DBUS_SESSION_BUS_ADDRESS="unix:path=$work/runtime/no-session-bus" \
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=$work/runtime/no-system-bus" \
        LD_LIBRARY_PATH="$bundle/lib" "$@" > "$work/$name.log" 2>&1 || result=$?
    printf '%s\t%s\n' "$name" "$result" >> "$work/status.tsv"
    [ "$result" = 0 ] || failed=1
}
for name in unit-tests-utils unit-tests-ei unit-tests-eis unit-tests-oeffis; do
    env LD_LIBRARY_PATH="$bundle/lib" ldd "$bundle/bin/$name" >> "$work/libraries.txt"
    run_test "$name" "$bundle/bin/$name" --log-visible debug
 done
run_test eierpecken-no-sigalrm "$bundle/bin/eierpecken" --log-visible debug
if [ "$mode" = normal ]; then
    run_test eierpecken "$bundle/bin/eierpecken" --log-visible debug --enable-sigalarm
fi
for name in test-build-libei test-build-libeis test-build-cxx-libei test-build-cxx-libeis; do
    run_test "$name" "$bundle/bin/$name"
done
if [ "$failed" != 0 ]; then echo "FAIL: inspect $work/status.tsv" >&2; exit 1; fi
printf 'PASS: compiled upstream libei tests (%s); portal Python and compositor checks not run\n' "$mode"
