#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Usage: qt5-qtbase-darwin-install-name.sh BMAKE NATIVE_MAKECONF PKGSRC NEW_WORK [BMAKE_ARG...]
#
# On Darwin the qt5 post-install step sets the install name of every
# installed library and plugin to its full path. qmake links plugins with
# little header space, and the LLVM install-name tool wrote a malformed
# image when the longer name did not fit, so the package check stopped with
# "cannot read image architectures". Link a probe library with the recipe's
# LDFLAGS, give it a long install name with the selected tool, and require
# a well-formed image that carries the new name.
set -eu
[ "$#" -ge 4 ] || { echo "Usage: $0 BMAKE NATIVE_MAKECONF PKGSRC NEW_WORK [BMAKE_ARG...]" >&2; exit 2; }
bmake=$1 conf=$2 pkgsrc=$3 work=$4
shift 4
for path in "$bmake" "$conf" "$pkgsrc" "$work"; do
	case "$path" in /*) ;; *) echo 'Use absolute paths' >&2; exit 2 ;; esac
done
[ ! -e "$work" ] || { echo "NEW_WORK must be new: $work" >&2; exit 2; }
q() { MAKECONF=$conf "$bmake" -C "$pkgsrc/x11/qt5-qtbase" MAKECONF="$conf" "$@" show-var VARNAME="$v" </dev/null 2>/dev/null; }
v=OPSYS; [ "$(q "$@")" = Darwin ] || { echo "$0: select a native Darwin build" >&2; exit 2; }
v=USE_CROSS_COMPILE; [ "$(q "$@" | tr A-Z a-z)" != yes ] || { echo "$0: select a native build" >&2; exit 2; }
v=LDFLAGS; ldflags=$(q "$@")
v=TOOLBASE; toolbase=$(q "$@")
v=EMBERBSD_DARWIN_INSTALL_NAME_TOOL; int=$(q "$@")
[ -n "$int" ] || int=install_name_tool
mkdir "$work"
# Several symbols give the probe a header the size of a small plugin's.
i=0; : >"$work/p.c"
while [ "$i" -lt 40 ]; do echo "int probe_$i(void) { return $i; }" >>"$work/p.c"; i=$((i + 1)); done
# shellcheck disable=SC2086
"$toolbase/bin/clang" -dynamiclib -o "$work/libprobe.dylib" "$work/p.c" \
    -Wl,-install_name,libprobe.dylib $ldflags >"$work/link.log" 2>&1 ||
	{ tail -3 "$work/link.log"; echo 'FAIL: cannot link the probe library'; exit 1; }
name=/$(printf '%0200d' 0 | tr 0 n)/qt5/plugins/imageformats/libprobe.dylib
"$int" -id "$name" "$work/libprobe.dylib" >"$work/int.log" 2>&1 ||
	{ tail -3 "$work/int.log"; echo "FAIL: $int cannot set the install name"; exit 1; }
id=$("$toolbase/bin/llvm-otool" -D "$work/libprobe.dylib" 2>"$work/otool.err" | sed -n 2p)
[ ! -s "$work/otool.err" ] || { cat "$work/otool.err"; echo 'FAIL: the library is malformed after the install name change'; exit 1; }
[ "$id" = "$name" ] || { echo "FAIL: the install name is '$id'"; exit 1; }
"$toolbase/bin/llvm-lipo" -archs "$work/libprobe.dylib" >/dev/null 2>&1 ||
	{ echo 'FAIL: lipo cannot read the library architectures'; exit 1; }
echo "PASS: qt5 libraries take a full-path install name with $int"
