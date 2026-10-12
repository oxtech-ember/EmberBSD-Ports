#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), build only host-side LLVM generators.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 LLVM_ARCHIVE NEW_WORK CMAKE NINJA" >&2; exit 2; }
archive=$1 work=$2 cmake=$3 ninja=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) echo 'Use paths without shell metacharacters.' >&2; exit 2 ;; esac
done
jobs=${JOBS:-3}
case "$jobs" in ''|*[!0-9]*|0) echo 'JOBS must be positive.' >&2; exit 2 ;; esac
[ -x "$cmake" ] && [ -x "$ninja" ]
: "${HOST_PYTHON:?Set HOST_PYTHON to the current build-host Python executable}"
case "$HOST_PYTHON" in /*) ;; *) exit 2;; esac
[ -x "$HOST_PYTHON" ]
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = \
    c44186a7762ed28954be72e5ff6df9808e0779d4f1bf014ecc4e7e211d31ee34 ]
mkdir "$work"
mkdir "$work/source"
source=llvm-project-23.1.3.src
tar -xf "$archive" -C "$work/source" "$source/llvm" "$source/cmake" \
    "$source/third-party" "$source/libc"
{
    shasum -a 256 "$archive" "$cmake" "$ninja" "$0"
    "$cmake" --version
    "$ninja" --version
    "$HOST_PYTHON" --version
    "${HOST_CC:-/usr/bin/cc}" --version
    "${HOST_CXX:-/usr/bin/c++}" --version
} > "$work/inputs.txt"
# Native here describes build-time generators only. The target recipe retains
# all normal/experimental backends, shared LLVM, static components and tests.
"$cmake" -S "$work/source/$source/llvm" -B "$work/native" -G Ninja \
    -DCMAKE_C_COMPILER="${HOST_CC:-/usr/bin/cc}" \
    -DCMAKE_CXX_COMPILER="${HOST_CXX:-/usr/bin/c++}" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM="$ninja" \
    -DPython3_EXECUTABLE="$HOST_PYTHON" \
    -DLLVM_TARGETS_TO_BUILD=Native -DLLVM_INCLUDE_TESTS=OFF \
    -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF \
    -DLLVM_ENABLE_ZLIB=OFF -DLLVM_ENABLE_ZSTD=OFF \
    -DLLVM_ENABLE_LIBXML2=OFF -DLLVM_ENABLE_TERMINFO=OFF \
    -DLLVM_ENABLE_LIBEDIT=OFF > "$work/configure.log" 2>&1
"$ninja" -C "$work/native" -j "$jobs" llvm-tblgen llvm-min-tblgen llvm-config \
    > "$work/build.log" 2>&1
for tool in llvm-tblgen llvm-min-tblgen llvm-config; do
    "$work/native/bin/$tool" --version
    shasum -a 256 "$work/native/bin/$tool" >> "$work/outputs.sha256"
done
printf 'Build-host tools: %s/native/bin\n' "$work"
