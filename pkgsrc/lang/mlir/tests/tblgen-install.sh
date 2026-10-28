#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# flang's standalone build runs the installed mlir-tblgen. Configure the
# real MLIR source with the recipe's CMake arguments against an installed
# LLVM and require the install rules to install mlir-tblgen, and the PLIST
# to list exactly the programs that the rules and post-install install.
# Usage: tblgen-install.sh CMAKE LLVM_CMAKE_DIR MLIR_SOURCE NEW_WORK
set -eu
[ "$#" = 4 ] || { echo 'usage: tblgen-install.sh CMAKE LLVM_CMAKE_DIR MLIR_SOURCE NEW_WORK' >&2; exit 2; }
cmake=$1 llvm=$2 src=$3 work=$4
for p in "$cmake" "$llvm" "$src" "$work"; do
	case "$p" in /*) ;; *) echo "not absolute: $p" >&2; exit 2 ;; esac
done
[ -f "$src/tools/mlir-tblgen/CMakeLists.txt" ] || { echo "not an MLIR source: $src" >&2; exit 2; }
[ ! -e "$work" ] || { echo "work must be new: $work" >&2; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
# Every literal -D on unconditional CMAKE_CONFIGURE_ARGS lines; make
# variables and the cross-only block are left to the cross-inputs test.
args=$(awk '/^\.if/ { depth++ } /^\.endif/ { depth-- }
    depth == 0 && /^CMAKE_CONFIGURE_ARGS\+=/ {
	for (i = 2; i <= NF; i++) if ($i ~ /^-D/ && $i !~ /\$/) print $i }' "$here/Makefile")
# Programs the recipe installs itself after the CMake install.
extra=$(awk '/INSTALL_PROGRAM.*CMAKE_BUILD_DIR}\/bin\// {
	sub(/.*CMAKE_BUILD_DIR}\/bin\//, ""); print $1 }' "$here/Makefile")
mkdir "$work"
# shellcheck disable=SC2086
"$cmake" -S "$src" -B "$work/b" -G Ninja -DLLVM_DIR="$llvm" \
    -DCMAKE_INSTALL_PREFIX=/usr/pkg $args > "$work/configure.log" 2>&1 ||
	{ tail -20 "$work/configure.log"; echo 'FAIL: configure'; exit 1; }
find "$work/b/tools" -name cmake_install.cmake -exec cat {} + |
    sed -n 's|.*TYPE EXECUTABLE FILES "[^"]*/bin/\([^"/]*\)".*|bin/\1|p' > "$work/rules"
for program in $extra; do
	grep -q "^build bin/$program:" "$work/b/build.ninja" ||
		{ echo "FAIL: post-install program $program is not built"; exit 1; }
	echo "bin/$program" >> "$work/rules"
done
sort -u "$work/rules" > "$work/installed"
grep -qx 'bin/mlir-tblgen' "$work/installed" ||
	{ echo 'FAIL: mlir-tblgen is not installed'; exit 1; }
grep '^bin/' "$here/PLIST" | sort -u > "$work/plist"
cmp -s "$work/installed" "$work/plist" ||
	{ echo 'FAIL: PLIST programs differ from the install rules:'; diff "$work/plist" "$work/installed"; exit 1; }
echo "PASS: MLIR installs $(tr '\n' ' ' < "$work/installed")"
