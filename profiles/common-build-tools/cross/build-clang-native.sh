#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), build the matching host Clang generator.
set -eu
[ "$#" = 5 ] || {
    echo "Usage: $0 LLVM_ARCHIVE LLVM_NATIVE NEW_WORK CMAKE NINJA" >&2
    exit 2
}
archive=$1 llvm=$2 work=$3 cmake=$4 ninja=$5
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) echo 'Use paths without shell metacharacters.' >&2; exit 2 ;; esac
done
jobs=${JOBS:-3}
case "$jobs" in ''|*[!0-9]*|0) echo 'JOBS must be positive.' >&2; exit 2 ;; esac
: "${HOST_PYTHON:?Set HOST_PYTHON to the build-host Python executable}"
case "$HOST_PYTHON" in /*) ;; *) exit 2 ;; esac
[ -x "$cmake" ] && [ -x "$ninja" ] && [ -x "$HOST_PYTHON" ]
[ -f "$llvm/lib/cmake/llvm/LLVMConfig.cmake" ]
[ "$("$llvm/bin/llvm-config" --version)" = 23.1.2 ]
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = \
    c98bbef08a2b4c2613cd50e9aa9ae7b69b1fe6c16b2c40373bc0ab6116fdf78a ]
mkdir "$work"
mkdir "$work/source"
source=llvm-project-23.1.2.src
tar -xf "$archive" -C "$work/source" "$source/clang" "$source/cmake"
{
    shasum -a 256 "$archive" "$cmake" "$ninja" "$0" \
        "$llvm/bin/llvm-config" "$llvm/bin/llvm-tblgen"
    "$cmake" --version
    "$ninja" --version
    "$HOST_PYTHON" --version
    "${HOST_CC:-/usr/bin/cc}" --version
    "${HOST_CXX:-/usr/bin/c++}" --version
} > "$work/inputs.txt"
# Reuse the native LLVM build made by build-llvm-native.sh. Only the generator
# runs on the host; this does not alter target Clang's tests or package contents.
"$cmake" -S "$work/source/$source/clang" -B "$work/native" -G Ninja \
    -DCMAKE_C_COMPILER="${HOST_CC:-/usr/bin/cc}" \
    -DCMAKE_CXX_COMPILER="${HOST_CXX:-/usr/bin/c++}" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM="$ninja" \
    -DPython3_EXECUTABLE="$HOST_PYTHON" \
    -DLLVM_DIR="$llvm/lib/cmake/llvm" -DLLVM_CMAKE_DIR="$llvm/lib/cmake/llvm" \
    -DLLVM_CONFIG="$llvm/bin/llvm-config" \
    -DLLVM_TABLEGEN="$llvm/bin/llvm-tblgen" \
    -DLLVM_INCLUDE_TESTS=OFF -DCLANG_INCLUDE_TESTS=OFF \
    > "$work/configure.log" 2>&1
"$ninja" -C "$work/native" -j "$jobs" clang-tblgen > "$work/build.log" 2>&1
"$work/native/bin/clang-tblgen" --version > "$work/version.txt"
shasum -a 256 "$work/native/bin/clang-tblgen" > "$work/outputs.sha256"
printf 'Build-host Clang generator: %s/native/bin/clang-tblgen\n' "$work"
