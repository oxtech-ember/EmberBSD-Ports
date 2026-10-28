#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Configure the real flang 23 source with the recipe's CMake arguments
# against installed LLVM/Clang and a separately installed MLIR. Require the
# recipe to find MLIR through its own prefix, to name only files that exist
# in REPLACE_BASH, to carry no GCC_REQD, and its PLIST and buildlink3.mk to
# list exactly the programs that the install rules install, symlinks included.
# Only the source elements that the recipe extracts are made available.
# Usage: recipe-install.sh CMAKE LLVM_PREFIX MLIR_PREFIX LLVM_PROJECT_SOURCE NEW_WORK
set -eu
[ "$#" = 5 ] || { echo 'usage: recipe-install.sh CMAKE LLVM_PREFIX MLIR_PREFIX LLVM_PROJECT_SOURCE NEW_WORK' >&2; exit 2; }
cmake=$1 llvm=$2 mlir=$3 project=$4 work=$5
for p in "$cmake" "$llvm" "$mlir" "$project" "$work"; do
	case "$p" in /*) ;; *) echo "not absolute: $p" >&2; exit 2 ;; esac
done
[ -f "$project/flang/tools/flang-driver/CMakeLists.txt" ] || { echo "not an llvm-project source: $project" >&2; exit 2; }
[ -f "$mlir/lib/cmake/mlir/MLIRConfig.cmake" ] || { echo "no MLIR in $mlir" >&2; exit 2; }
[ ! -e "$work" ] || { echo "work must be new: $work" >&2; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
fail=0
src=$work/src/flang
if grep -nE '^[[:space:]]*GCC_REQD[[:space:]]*\+?=' "$here/Makefile"; then
	echo 'FAIL: the recipe pins GCC_REQD'; fail=1
fi
for f in $(sed -n 's/^REPLACE_BASH[+]*=[[:space:]]*//p' "$here/Makefile"); do
	[ -f "$project/flang/$f" ] || { echo "FAIL: REPLACE_BASH names a missing file: $f"; fail=1; }
done
args=$(sed -n 's/^CMAKE_CONFIGURE_ARGS+=[[:space:]]*\(-D[^[:space:]]*\).*/\1/p' "$here/Makefile" |
    sed -e "s|\${BUILDLINK_PREFIX.mlir}|$mlir|" -e "s|\${BUILDLINK_PREFIX.[a-z]*}|$llvm|")
mkdir "$work" "$work/src"
# lang/llvm/version.mk: EXTRACT_ELEMENTS are PKGBASE, cmake, runtimes, third-party, libc.
cp -R "$project/flang" "$work/src/flang"
for e in cmake runtimes third-party libc; do ln -s "$project/$e" "$work/src/$e"; done
# shellcheck disable=SC2086
if ! "$cmake" -S "$src" -B "$work/b" -G Ninja -DCMAKE_INSTALL_PREFIX=/usr/pkg \
    $args > "$work/configure.log" 2>&1; then
	grep -m3 'Could not find\|CMake Error' "$work/configure.log" || true
	echo 'FAIL: configure'; exit 1
fi
find "$work/b" -name cmake_install.cmake -exec cat {} + |
    sed -n -e 's|.*TYPE EXECUTABLE FILES "[^"]*/bin/\([^"/]*\)".*|bin/\1|p' \
        -e 's|^ *"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/\([^"/]*\)".*|bin/\1|p' \
        -e 's|^ *install_symlink("\([^"]*\)" "[^"]*" "bin".*|bin/\1|p' |
    sort -u > "$work/installed"
grep -qx 'bin/flang' "$work/installed" || { echo 'FAIL: bin/flang is not installed'; fail=1; }
grep '^bin/' "$here/PLIST" | sort -u > "$work/plist"
cmp -s "$work/installed" "$work/plist" ||
	{ echo 'FAIL: PLIST programs differ from the install rules:'; diff "$work/plist" "$work/installed" || true; fail=1; }
sed -n 's/^BUILDLINK_FILES.flang+=[[:space:]]*//p' "$here/buildlink3.mk" | sort -u > "$work/bl3"
comm -23 "$work/bl3" "$work/installed" > "$work/bl3-missing"
[ ! -s "$work/bl3-missing" ] ||
	{ echo "FAIL: buildlink3.mk names programs that are not installed: $(tr '\n' ' ' < "$work/bl3-missing")"; fail=1; }
[ "$fail" = 0 ] || exit 1
echo "PASS: flang installs $(tr '\n' ' ' < "$work/installed")"
