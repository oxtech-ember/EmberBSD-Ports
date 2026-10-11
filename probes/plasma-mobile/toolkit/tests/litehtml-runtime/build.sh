#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), run unchanged upstream encoding tests.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 CROSS_TOOLS SYSROOT TEST_ARCHIVE NEW_WORK" >&2; exit 2; }
tools=$1 sysroot=$2 archive=$3 work=$4
: "${CMAKE:?Set the native CMake executable}"
: "${NINJA:?Set the native Ninja executable}"
for path in "$tools" "$sysroot" "$archive" "$work" "$CMAKE" "$NINJA"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = \
    8d831a6e48f1f319a2597236fd865a1a287e10f6485a7914296145b2263b2032 ]
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$work"
mkdir "$work/source"
tar -xf "$archive" --strip-components=1 -C "$work/source" \
    litehtml-tests-2bb4d22d7d2a0916e4ec69e30d71b39bfe3b7b8a/encodings_test.cpp
"$CMAKE" -S "$src" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" \
    -DCMAKE_SYSTEM_NAME=NetBSD -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
    -DCMAKE_SYSROOT="$sysroot" -DCMAKE_FIND_ROOT_PATH="$sysroot" \
    -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
    -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY \
    -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
    -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY \
    -DCMAKE_PREFIX_PATH=/usr/pkg \
    -DCMAKE_CXX_COMPILER="$tools/bin/aarch64--netbsd-g++" \
    -DCMAKE_CXX_FLAGS="-B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
    -DCMAKE_EXE_LINKER_FLAGS="-L$sysroot/usr/pkg/gcc16/lib -L$sysroot/usr/pkg/lib" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_INSTALL_RPATH='/usr/pkg/gcc16/lib;/usr/pkg/lib' \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON -DUPSTREAM_TEST_SOURCE="$work/source"
"$CMAKE" --build "$work/build" --parallel 2
shasum -a 256 "$src"/* "$archive" "$work/build/litehtml-runtime" > "$work/inputs-output.sha256"
