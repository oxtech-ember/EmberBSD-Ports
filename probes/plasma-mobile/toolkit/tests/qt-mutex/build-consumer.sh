#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted cross build for the public Qt mutex consumer.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 CROSS_TOOLS SYSROOT NEW_OUTPUT" >&2; exit 2; }
tools=$1 sysroot=$2 output=$3
for path in "$tools" "$sysroot" "$output"; do
    case "$path" in /*) ;; *) echo 'Absolute paths are required' >&2; exit 2;; esac
done
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$output"
"$tools/bin/aarch64--netbsd-g++" --sysroot="$sysroot" \
    -B"$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
    -std=c++20 -O2 -g -Wall -Wextra -Werror -pthread \
    -I"$sysroot/usr/pkg/qt6/include" -I"$sysroot/usr/pkg/qt6/include/QtCore" \
    "$src/runtime-consumer.cpp" -L"$sysroot/usr/pkg/qt6/lib" -lQt6Core \
    -L"$sysroot/usr/pkg/gcc16/lib" -L"$sysroot/usr/pkg/lib" \
    -Wl,-rpath,/usr/pkg/qt6/lib -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/lib \
    -o "$output/qt-mutex-consumer"
"$tools/bin/aarch64--netbsd-readelf" -h -d "$output/qt-mutex-consumer" > "$output/elf.txt"
shasum -a 256 "$src/runtime-consumer.cpp" \
    "$sysroot/usr/pkg/qt6/include/QtCore/qmutex.h" \
    "$sysroot/usr/pkg/qt6/lib/libQt6Core.so.6" \
    "$output/qt-mutex-consumer" > "$output/inputs-output.sha256"
