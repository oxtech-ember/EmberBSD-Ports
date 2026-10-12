#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed generator and upstream core checks.
set -eu
[ "$#" = 3 ] || { echo "Usage: sonnet-runtime.sh VERIFIED_FIXTURES ASPELL_DICTIONARIES NEW_OUTPUT" >&2; exit 2; }
fixtures=$(CDPATH= cd -- "$1" && pwd)
dictionaries=$(CDPATH= cd -- "$2" && pwd)
umask 077
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
PATH=/usr/pkg/bin:/usr/sbin:/usr/bin:/bin:/sbin; export PATH
unset LD_LIBRARY_PATH LD_PRELOAD
ulimit -c 0
mkdir "$work/home" "$work/runtime"
HOME="$work/home" XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal LC_ALL=C.UTF-8
ASPELL_CONF="dict-dir $dictionaries; local-data-dir $dictionaries"
export HOME XDG_RUNTIME_DIR QT_QPA_PLATFORM LC_ALL ASPELL_CONF
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-sonnet > "$work/package.txt"
parsetrigrams6 "$fixtures/trigrams" > "$work/target.map"
cmp "$fixtures/native.map" "$work/target.map"
sha256 "$work/target.map" > "$work/model.sha256"
result=0
parsetrigrams6 > "$work/no-argument.log" 2>&1 || result=$?
[ "$result" = 1 ]
failed=0
for program in test_filter test_settings test_autodetect test_core test_suggest; do
    ldd "$fixtures/$program" > "$work/$program.ldd"
    ! grep -q 'not found' "$work/$program.ldd"
    result=0
    timeout -k 5 120 "$fixtures/$program" > "$work/$program.log" 2>&1 || result=$?
    printf '%s\n' "$result" > "$work/$program.status"
    cat "$work/$program.log"
    [ "$result" = 0 ] || failed=1
done
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
[ "$failed" = 0 ]
echo 'PASS: native/target language models match; installed Sonnet core suites pass'
