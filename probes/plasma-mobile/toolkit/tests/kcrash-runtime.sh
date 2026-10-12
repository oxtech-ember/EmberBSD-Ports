#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), upstream crash recovery on installed libraries.
set -eu
[ "$#" = 2 ] || { echo 'Usage: kcrash-runtime.sh UPSTREAM_BINARIES_AND_DATA NEW_OUTPUT' >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
umask 077
mkdir "$work/home" "$work/runtime"
[ -x "$binaries/test_crasher" ] && [ -d "$binaries/core_patterns" ]
ulimit -c 0
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-kcrash > "$work/package.txt"
ldd "$binaries/test_crasher" > "$work/test_crasher.ldd"
sha256 "$binaries/test_crasher" > "$work/tests.sha256"
failed=0
for name in coreconfigtest metadatatest kcrashtest; do
    result=0
    timeout -k 5 120 env -i PATH="$PATH" LC_ALL=C.UTF-8 HOME="$work/home" \
        XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal \
        "$binaries/$name" > "$work/$name.log" 2>&1 || result=$?
    printf '%s %s\n' "$name" "$result" >> "$work/status.txt"
    tail -n 3 "$work/$name.log"
    sha256 "$binaries/$name" >> "$work/tests.sha256"
    [ "$result" = 0 ] || failed=1
done
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after" || failed=1
[ "$failed" = 0 ] || exit 1
echo 'PASS: KCrash recovery and metadata; DrKonqi and desktop integration untested'
