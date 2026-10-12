#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), verify the upstream native build tools.
set -eu
[ "$#" = 2 ] || { echo 'Usage: prepare-llvm-macos.sh ARCHIVE NEW_WORK' >&2; exit 2; }
archive=$1 work=$2
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Unsafe path' >&2; exit 2;; esac
done
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ]
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = \
    3dcfd88aec10be204a24037bcb0dc0ad777882e9dbe8ac60e2639060d8a794b1 ]
mkdir "$work"
shasum -a 256 "$archive" "$0" > "$work/inputs.sha256"
# Extract the complete authenticated upstream SDK. CMake exports refer to
# auxiliary tools and libraries, so a hand-picked subset is not equivalent.
tar -xf "$archive" -C "$work"
prefix=$work/LLVM-23.1.3-macOS-ARM64
[ "$("$prefix/bin/llvm-config" --version)" = 23.1.3 ]
for tool in llvm-tblgen clang-tblgen; do
    "$prefix/bin/$tool" --version > "$work/$tool.version"
    grep -q 'LLVM version 23.1.3' "$work/$tool.version"
    shasum -a 256 "$prefix/bin/$tool" >> "$work/outputs.sha256"
done
for file in lib/libclang.dylib lib/libclangHandleCXX.a lib/libLTO.dylib \
    lib/cmake/llvm/LLVMConfig.cmake lib/cmake/clang/ClangConfig.cmake; do
    [ -s "$prefix/$file" ]
    shasum -a 256 "$prefix/$file" >> "$work/outputs.sha256"
done
"$prefix/bin/clang" --version > "$work/clang.version"
otool -L "$prefix/lib/libclang.dylib" > "$work/libclang.dependencies"
printf 'Verified native LLVM/Clang SDK: %s\n' "$prefix"
