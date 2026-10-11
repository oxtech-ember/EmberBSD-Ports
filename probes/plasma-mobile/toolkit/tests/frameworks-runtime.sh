#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed Frameworks runtime acceptance.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 UPSTREAM_TEST_BINARIES NEW_RESULTS" >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
prefix=${PREFIX:-/usr/pkg}
case "$prefix" in /*) ;; *) echo 'Absolute PREFIX required' >&2; exit 2;; esac
PATH="$prefix/bin:$prefix/sbin:/usr/bin:/usr/sbin:/bin:/sbin"; export PATH
for name in kdirwatch_default_unittest kcountrytest kcountrysubdivisiontest ktimezonetest ki18ndeclarativetest; do
    [ -x "$binaries/$name" ] || { echo "Missing upstream test: $name" >&2; exit 2; }
done
umask 077
mkdir "$work/home" "$work/cache" "$work/data" "$work/config" "$work/runtime"
sysctl kern.boottime > "$work/boot.before"
failed=0
for name in kdirwatch_default_unittest kcountrytest kcountrysubdivisiontest ktimezonetest ki18ndeclarativetest; do
    result=0
    timeout -k 5 80 env -i PATH="$PATH" LC_ALL=C.UTF-8 HOME="$work/home" \
        XDG_CACHE_HOME="$work/cache" XDG_DATA_HOME="$work/data" \
        XDG_CONFIG_HOME="$work/config" XDG_RUNTIME_DIR="$work/runtime" \
        XDG_DATA_DIRS="$prefix/share" QT_QPA_PLATFORM=minimal \
        QT_QUICK_BACKEND=software QT_LOGGING_RULES='kf.coreaddons.debug=true' \
        "$binaries/$name" -iterations 1 > "$work/$name.log" 2>&1 || result=$?
    printf '%s %s\n' "$name" "$result" >> "$work/status.txt"
    tail -n 3 "$work/$name.log"
    sha256 "$binaries/$name" >> "$work/tests.sha256"
    ldd "$binaries/$name" > "$work/$name.ldd"
    [ "$result" = 0 ] || failed=1
done
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after" || failed=1
[ "$failed" = 0 ] || exit 1
echo 'PASS: installed Frameworks file events and locale APIs; no GPU/session claim'
