#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: qt5-qtbase-llvm-ranlib.sh RECIPE_DIR DISTFILE HOST_PREFIX NEW_WORK
#
# On macOS the qtbase build loads mkspecs/features/mac/no_warn_empty_obj_files
# .prf, which appended the cctools-only option -no_warning_for_no_symbols to
# QMAKE_RANLIB. The native phase of a cross build uses llvm-ranlib from the
# host tool prefix, which rejects the option, so the first static library
# (libQt5Bootstrap.a) failed. Patch the feature file with the recipe patches,
# evaluate it with qmake for llvm-ranlib and for the cctools name, and run
# the resulting llvm-ranlib command on an archive made like qmake makes it.
# RECIPE_DIR is the x11/qt5-qtbase recipe; HOST_PREFIX supplies bsdtar,
# gpatch, clang, llvm-ar, llvm-ranlib, llvm-nm and qt6/bin/qmake (or QMAKE).
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 RECIPE_DIR DISTFILE HOST_PREFIX NEW_WORK" >&2; exit 2; }
recipe=$1 distfile=$2 host=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
qmake=${QMAKE:-$host/qt6/bin/qmake}
src=$(basename "$distfile" .tar.xz | sed "s/-opensource//")
prf=mkspecs/features/mac/no_warn_empty_obj_files.prf
"$host/bin/bsdtar" -xf "$distfile" -C "$work" "$src/$prf"
for p in "$recipe"/patches/patch-mkspecs_features_mac_*; do
	[ -f "$p" ] || continue
	"$host/bin/gpatch" -s -d "$work/$src" -p0 -F0 < "$p"
done
# Print QMAKE_RANLIB after the feature file for a given ranlib command.
eval_ranlib() {
	d=$work/q-$1
	mkdir "$d"
	cat > "$d/t.pro" <<PRO
TEMPLATE = aux
QMAKE_RANLIB = $2
include($work/$src/$prf)
write_file(\$\$OUT_PWD/ranlib.txt, QMAKE_RANLIB)
PRO
	(cd "$d" && "$qmake" -nocache t.pro >/dev/null 2>&1)
	tr '\n' ' ' < "$d/ranlib.txt" | sed 's/ $//'
}
llvm=$(eval_ranlib llvm "$host/bin/llvm-ranlib")
cctools=$(eval_ranlib cctools ranlib)
case "$cctools" in
"ranlib -no_warning_for_no_symbols") ;;
*) echo "FAIL: cctools ranlib lost its option: '$cctools'"; exit 1 ;;
esac
# One object with symbols and one without, archived without an index.
echo 'int qt_ranlib_probe(void) { return 0; }' > "$work/a.c"
: > "$work/empty.c"
"$host/bin/clang" -c -o "$work/a.o" "$work/a.c"
"$host/bin/clang" -c -o "$work/empty.o" "$work/empty.c"
"$host/bin/llvm-ar" cq -S "$work/lib.a" "$work/a.o" "$work/empty.o"
# shellcheck disable=SC2086 # the evaluated command line.
if ! out=$($llvm "$work/lib.a" 2>&1); then
	echo "FAIL: qmake ranlib command '$llvm' failed: $out"
	exit 1
fi
if ! "$host/bin/llvm-nm" --print-armap "$work/lib.a" 2>/dev/null | grep -q qt_ranlib_probe; then
	echo "FAIL: '$llvm' wrote no archive index"
	exit 1
fi
echo "PASS: llvm-ranlib command '$llvm'; cctools command '$cctools'"
