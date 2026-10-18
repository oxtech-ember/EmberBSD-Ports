#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the actual selected cross runtime.
set -eu
LC_ALL=C
export LC_ALL
[ "$#" -ge 4 ] || { echo 'Usage: check-gcc16-atomic.sh SYSROOT TRIPLET READELF CXX [FLAGS...]' >&2; exit 2; }
sysroot=$1
triplet=$2
readelf=$3
shift 3
case "$sysroot:$readelf:$1" in /*:/*:/*) ;; *) echo 'Absolute tool and sysroot paths are required' >&2; exit 2 ;; esac
case "$triplet" in
    aarch64--netbsd) machine=AArch64 ;;
    x86_64--netbsd) machine='Advanced Micro Devices X86-64' ;;
    *) echo 'Unsupported WebKit cross triplet' >&2; exit 2 ;;
esac
[ "$("$@" -dumpmachine)" = "$triplet" ] || { echo 'Compiler target mismatch' >&2; exit 1; }
[ "$("$@" -dumpfullversion)" = 16.2.0 ] || { echo 'WebKit requires the common GCC 16.2.0 provider' >&2; exit 1; }
selected=$("$@" -print-file-name=libatomic.so)
expected=$sysroot/usr/pkg/gcc16/lib/libatomic.so
[ -f "$selected" ] && [ "$selected" -ef "$expected" ] || {
    echo 'The driver must select libatomic.so from the staged GCC16 provider' >&2; exit 1;
}
header=$("$readelf" -h "$selected")
printf '%s\n' "$header" | grep -q 'Class:.*ELF64'
printf '%s\n' "$header" | grep -q 'Data:.*little endian'
[ "$(printf '%s\n' "$header" | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')" = "$machine" ]
dynamic=$("$readelf" -d "$selected")
[ "$(printf '%s\n' "$dynamic" | sed -n 's/.*(SONAME).*\[\([^]]*\)\].*/\1/p')" = libatomic.so.3 ] || {
    echo 'The selected GCC16 libatomic SONAME is not libatomic.so.3' >&2; exit 1;
}
printf 'GCC16 target atomic provider: %s\n' "$selected"
