#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross-build on the development host.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 CROSS_TOOLS SYSROOT NEW_OUTPUT" >&2; exit 2; }
tools=$1 sysroot=$2 output=$3
for path in "$tools" "$sysroot" "$output"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
done
[ ! -e "$output" ] || { echo 'Output already exists' >&2; exit 2; }
compiler=$tools/bin/aarch64--netbsd-g++
"$compiler" -dumpfullversion | grep -Eq '^16\.'
source=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/diagnose.cpp
"$compiler" --sysroot="$sysroot" \
    -B"$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
    -std=c++20 -O2 -g -Wall -Wextra -Werror -pthread \
    -I"$sysroot/usr/pkg/qt6/include" -I"$sysroot/usr/pkg/qt6/include/QtCore" \
    -I"$sysroot/usr/pkg/qt6/include/QtGui" "$source" \
    -L"$sysroot/usr/pkg/qt6/lib" -L"$sysroot/usr/pkg/gcc16/lib" \
    -Wl,-rpath,/usr/pkg/qt6/lib -Wl,-rpath,/usr/pkg/gcc16/lib \
    -Wl,-rpath-link,"$sysroot/usr/pkg/lib" -lQt6Gui -lQt6Core -o "$output"
file "$output"
shasum -a 256 "$source" "$output"
