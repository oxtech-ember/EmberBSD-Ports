#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed upstream archive tests.
set -eu
[ "$#" = 2 ] || { echo 'Usage: archive-runtime.sh UPSTREAM_TEST_DIRECTORY NEW_OUTPUT' >&2; exit 2; }
inputs=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
umask 077
mkdir "$work/home" "$work/runtime" "$work/scratch"
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-karchive > "$work/package.txt"
cd "$work/scratch"
for program in karchivetest kfiltertest; do
    ldd "$inputs/$program" > "$work/$program.ldd"
    ! grep -q 'not found' "$work/$program.ldd"
    grep -q '/usr/pkg/lib/libKF6Archive' "$work/$program.ldd"
    sha256 "$inputs/$program" >> "$work/inputs.sha256"
set --
if [ "$program" = karchivetest ] && [ "${KARCHIVE_SKIP_LARGE_UNPACK:-no}" = yes ]; then
    QT_QPA_PLATFORM=minimal "$inputs/$program" -functions > "$work/functions.txt"
    grep -Fxq 'test7ZipLargeUnpackSize()' "$work/functions.txt"
    # QtTest reports identifier-only names, verified before shell splitting.
    sed '/^test7ZipLargeUnpackSize()$/d; s/()$//' "$work/functions.txt" > "$work/selected.txt"
    ! grep -Eqv '^[A-Za-z_][A-Za-z0-9_]*$' "$work/selected.txt"
    set -- $(cat "$work/selected.txt")
    [ "$#" -gt 0 ]
    echo 'NOT RUN: test7ZipLargeUnpackSize (explicit resource exclusion)' | tee "$work/exclusions.txt"
fi
result=0
    timeout -k 5 180 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 TZ=UTC \
        XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal \
        "$inputs/$program" "$@" > "$work/$program.log" 2>&1 || result=$?
    cat "$work/$program.log"
    [ "$result" = 0 ] || exit "$result"
done
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: selected installed KArchive archive/filter tests; consult exclusions.txt for any untested case'
