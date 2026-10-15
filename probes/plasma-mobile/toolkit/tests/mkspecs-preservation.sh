#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted Qt recipe regression.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 QTBASE_RECIPE NEW_WORK" >&2; exit 2; }
recipe=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
mkdir -p "$work/source/mkspecs/netbsd-g++" "$work/source/mkspecs/features" "$work/source/mkspecs/devices"
printf 'pkgsrc configuration\n' > "$work/source/qmake.conf"
printf 'old platform configuration\n' > "$work/source/mkspecs/netbsd-g++/qmake.conf"
printf 'old patch backup\n' > "$work/source/mkspecs/netbsd-g++/qmake.conf.orig"
printf 'old feature patch backup\n' > "$work/source/mkspecs/features/toolchain.prf.orig"
printf 'PKG_CONFIG_EXECUTABLE = /build/tool\n' > "$work/source/mkspecs/qmodule.pri"
printf 'version = 1\n' > "$work/source/mkspecs/REUSE.toml"
cp "$work/source/mkspecs/qmodule.pri" "$work/qmodule.expected"
cp "$work/source/mkspecs/REUSE.toml" "$work/reuse.expected"
{
    printf 'WRKSRC=%s/source\nCP=cp\nRM=rm\nTEST=test\nall:\n' "$work"
    awk '/^\tfor dir in .*mkspecs/ { copying=1 } copying { print } copying && /^\tdone$/ { exit }' "$recipe/Makefile"
} > "$work/Makefile"
for run in 1 2; do
    "${BMAKE:-bmake}" -r -m / -f "$work/Makefile" 2> "$work/stderr.log"
    if [ -s "$work/stderr.log" ]; then
        cat "$work/stderr.log" >&2
        exit 1
    fi
    cmp "$work/source/qmake.conf" "$work/source/mkspecs/netbsd-g++/qmake.conf"
    cmp "$work/qmodule.expected" "$work/source/mkspecs/qmodule.pri"
    cmp "$work/reuse.expected" "$work/source/mkspecs/REUSE.toml"
    [ ! -f "$work/source/mkspecs/netbsd-g++/qmake.conf.orig" ]
    [ ! -f "$work/source/mkspecs/features/toolchain.prf.orig" ]
    [ ! -e "$work/source/mkspecs/features/qmake.conf" ]
    [ ! -e "$work/source/mkspecs/devices/qmake.conf" ]
    if grep -qx 'qt6/mkspecs/devices/qmake.conf' "$recipe/PLIST"; then
        echo 'PLIST requires a fabricated device configuration' >&2
        exit 1
    fi
done
echo 'PASS: Qt recipe preserves generated metadata and licenses across reconfiguration'
