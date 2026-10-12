#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), unchanged upstream model tests on installed Qt/KF.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 UPSTREAM_BINARIES NEW_OUTPUT" >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
names='kcolumnheadersmodeltest kdescendantsproxymodel_smoketest
kdescendantsproxymodeltest kextracolumnsproxymodeltest klinkitemselectionmodeltest
kmodelindexproxymappertest knumbermodeltest krearrangecolumnsproxymodeltest
kselectionproxymodeltest kselectionproxymodel_smoketest krolenames_qml
ksortfilterproxymodel_qml bihash_functionalitytest'
umask 077
mkdir "$work/home" "$work/cache" "$work/data" "$work/config" "$work/runtime"
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-kitemmodels > "$work/package.txt"
# Upstream's private test helper is not part of the installed KF package.
helper=$(CDPATH= cd -- "$binaries/../lib" && pwd)
[ -f "$helper/libproxymodeltestsuite.so" ]
for file in "$helper/"*; do
    [ "${file##*/}" = libproxymodeltestsuite.so ] || {
        echo 'Unexpected library in private test helper directory' >&2; exit 2;
    }
done
sha256 "$helper/libproxymodeltestsuite.so" > "$work/helper.sha256"
failed=0
for name in $names; do
    [ -x "$binaries/$name" ] || { echo "Missing test: $name" >&2; exit 2; }
    result=0
    timeout -k 5 120 env -i PATH="$PATH" LC_ALL=C.UTF-8 HOME="$work/home" \
        XDG_CACHE_HOME="$work/cache" XDG_DATA_HOME="$work/data" \
        XDG_CONFIG_HOME="$work/config" XDG_RUNTIME_DIR="$work/runtime" \
        XDG_DATA_DIRS=/usr/pkg/share QT_QPA_PLATFORM=minimal LD_LIBRARY_PATH="$helper" \
        "$binaries/$name" > "$work/$name.log" 2>&1 || result=$?
    printf '%s %s\n' "$name" "$result" >> "$work/status.txt"
    tail -n 3 "$work/$name.log"
    sha256 "$binaries/$name" >> "$work/tests.sha256"
    env LD_LIBRARY_PATH="$helper" ldd "$binaries/$name" > "$work/$name.ldd"
    [ "$result" = 0 ] || failed=1
done
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after" || failed=1
[ "$failed" = 0 ] || exit 1
echo 'PASS: installed Frameworks model APIs and QML bindings; no desktop claim'
