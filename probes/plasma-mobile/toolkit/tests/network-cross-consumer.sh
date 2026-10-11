#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compile on the host; run only on EmberBSD.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 CROSS_TOOLS SYSROOT NEW_WORK" >&2; exit 2; }
tools=$1 sysroot=$2 work=$3
for path in "$tools" "$sysroot" "$work"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths' >&2; exit 2;; esac
done
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$work"
"$tools/bin/aarch64--netbsd-gcc" --sysroot="$sysroot" \
    -B"$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
    -I"$sysroot/usr/pkg/include" -L"$sysroot/usr/pkg/lib" \
    -L"$sysroot/usr/pkg/gcc16/lib" -Wl,-rpath,/usr/pkg/lib \
    -Wl,-rpath,/usr/pkg/gcc16/lib -Wall -Wextra -Werror \
    "$src/network-consumer.c" -lcurl -lidn2 -o "$work/consumer"
file "$work/consumer"
