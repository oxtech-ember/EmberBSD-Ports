#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build an ICU consumer on the development host.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 CROSS_TOOLS SYSROOT HOST_GENERATED_FIXTURES NEW_WORK" >&2; exit 2; }
tools=$1 sysroot=$2 fixtures=$3 work=$4
for path in "$tools" "$sysroot" "$fixtures" "$work"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths' >&2; exit 2;; esac
done
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$work"
cp "$fixtures/en.res" "$fixtures/emberprobe.dat" "$work/"
"$tools/bin/aarch64--netbsd-gcc" --sysroot="$sysroot" \
    -B"$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
    -I"$sysroot/usr/pkg/include" -L"$sysroot/usr/pkg/lib" \
    -L"$sysroot/usr/pkg/gcc16/lib" -Wl,-rpath,/usr/pkg/lib \
    -Wl,-rpath,/usr/pkg/gcc16/lib -std=c23 -O2 -g -Wall -Wextra -Werror \
    -fsanitize=undefined -fsanitize-trap=undefined \
    "$src/icu-consumer.c" -licui18n -licuuc -licudata -o "$work/consumer"
cp "$src/icu-installed.sh" "$work/run.sh"
file "$work/consumer"
echo 'Built target test. Copy this directory to EmberBSD and run: sh run.sh .'
