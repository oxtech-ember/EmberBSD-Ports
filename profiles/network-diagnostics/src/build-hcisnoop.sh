#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross-builds hcisnoop with the common
# GCC16 cross driver against the accepted EmberBSD sysroot.
set -eu
[ "$#" -eq 3 ] || { echo 'Usage: build-hcisnoop.sh CROSS_PREFIX SYSROOT NEW_WORK' >&2; exit 2; }
prefix=$1 sysroot=$2 work=$3
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work already exists' >&2; exit 2; }
cc=$prefix/bin/aarch64--netbsd-gcc
[ "$("$cc" -dumpmachine)" = aarch64--netbsd ]
[ "$("$cc" -dumpfullversion)" = 16.2.0 ]
for file in usr/include/netbt/hci.h usr/include/sys/endian.h \
    usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/crtbegin.o; do
    [ -f "$sysroot/$file" ] || { echo "Missing sysroot input: $file" >&2; exit 1; }
done
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
mkdir "$work"
"$cc" -O2 -g --sysroot="$sysroot" \
    -B"$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
    -L"$sysroot/usr/pkg/gcc16/lib" -Wl,-rpath,/usr/pkg/gcc16/lib \
    "$here/hcisnoop.c" -o "$work/hcisnoop"
file_out=$("$prefix/bin/aarch64--netbsd-readelf" -h "$work/hcisnoop")
echo "$file_out" | grep -q 'Machine:.*AArch64'
echo "$file_out" | grep -q 'Type:.*EXEC'
echo "Built $work/hcisnoop"
