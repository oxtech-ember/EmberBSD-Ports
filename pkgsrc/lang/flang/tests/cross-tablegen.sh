#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Configure the patched flang 23 source the way a cross build does: LLVM,
# Clang and MLIR come from the target sysroot through the recipe's CMake
# arguments, and the recipe names the build-host mlir-tblgen. Require every
# generated TableGen rule to run that build-host program, never the target
# mlir-tblgen that the sysroot's MLIRConfig.cmake names.
# Usage: cross-tablegen.sh CMAKE SYSROOT HOST_MLIR_TBLGEN LLVM_PROJECT_SOURCE NEW_WORK
set -eu
[ "$#" = 5 ] || { echo 'usage: cross-tablegen.sh CMAKE SYSROOT HOST_MLIR_TBLGEN LLVM_PROJECT_SOURCE NEW_WORK' >&2; exit 2; }
cmake=$1 sysroot=$2 tblgen=$3 project=$4 work=$5
for p in "$cmake" "$sysroot" "$tblgen" "$project" "$work"; do
	case "$p" in /*) ;; *) echo "not absolute: $p" >&2; exit 2 ;; esac
done
[ -f "$sysroot/usr/pkg/lib/cmake/mlir/MLIRConfig.cmake" ] || { echo "no target MLIR in $sysroot" >&2; exit 2; }
"$tblgen" --version > /dev/null || { echo "not a build-host program: $tblgen" >&2; exit 2; }
[ -f "$project/flang/CMakeLists.txt" ] || { echo "not an llvm-project source: $project" >&2; exit 2; }
[ ! -e "$work" ] || { echo "work must be new: $work" >&2; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
mkdir "$work" "$work/src"
# lang/llvm/version.mk: EXTRACT_ELEMENTS are PKGBASE, cmake, runtimes, third-party, libc.
cp -R "$project/flang" "$work/src/flang"
for e in cmake runtimes third-party libc; do ln -s "$project/$e" "$work/src/$e"; done
for p in "$here"/patches/patch-*; do
	(cd "$work/src/flang" && patch -s -p0 -F0 < "$p") || { echo "FAIL: $p does not apply"; exit 1; }
done
# The recipe's arguments as a cross build expands them.
args=$(sed -n 's/^CMAKE_CONFIGURE_ARGS+=[[:space:]]*\(-D[^[:space:]]*\).*/\1/p' "$here/Makefile" |
    sed -e "s|\${_CROSS_DESTDIR:U}|$sysroot|" -e "s|\${BUILDLINK_PREFIX.[a-z]*}|/usr/pkg|" \
        -e "s|\${EMBERBSD_MLIR_NATIVE_TOOLS:Q}/mlir-tblgen|$tblgen|")
# shellcheck disable=SC2086
if ! "$cmake" -S "$work/src/flang" -B "$work/b" -G Ninja -DCMAKE_INSTALL_PREFIX=/usr/pkg \
    $args > "$work/configure.log" 2>&1; then
	grep -m3 'Could not find\|CMake Error' "$work/configure.log" || true
	echo 'FAIL: configure'; exit 1
fi
grep -o '[^[:space:]"]*mlir-tblgen[^[:space:]"]*' "$work/b/build.ninja" | sort -u > "$work/tblgen"
[ -s "$work/tblgen" ] || { echo 'FAIL: no mlir-tblgen rule was generated'; exit 1; }
if grep -vxF "$tblgen" "$work/tblgen"; then
	echo 'FAIL: TableGen rules run a program other than the build-host mlir-tblgen'; exit 1
fi
echo "PASS: every MLIR TableGen rule runs $tblgen"
