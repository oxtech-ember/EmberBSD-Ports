#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Guard regression without compiling a target.
set -eu
[ "$#" = 3 ] || { echo 'Usage: cross-guards.sh GCC_PREFIX SYSROOT NEW_RESULTS' >&2; exit 2; }
compiler=$1 sysroot=$2 out=$3
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
recipe=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
mkdir -p "$out/preserved"
printf 'keep this file\n' > "$out/preserved/marker"
printf 'invalid source\n' > "$out/corrupt.tar.gz"
status=0
sh "$recipe/cross-build.sh" "$compiler" "$sysroot" "$out/corrupt.tar.gz" "$out/preserved" > "$out/existing.log" 2>&1 || status=$?
[ "$status" = 2 ] && [ "$(cat "$out/preserved/marker")" = 'keep this file' ]
grep -Fx 'Output path already exists.' "$out/existing.log" > /dev/null
ln -s "$out/preserved" "$out/link"
status=0
sh "$recipe/cross-build.sh" "$compiler" "$sysroot" "$out/corrupt.tar.gz" "$out/link" > "$out/symlink.log" 2>&1 || status=$?
[ "$status" = 2 ] && [ -L "$out/link" ]
status=0
sh "$recipe/cross-build.sh" "$compiler" "$sysroot" "$out/corrupt.tar.gz" "$out/rejected" > "$out/checksum.log" 2>&1 || status=$?
[ "$status" -ne 0 ] && [ ! -e "$out/rejected" ]
grep 'FAILED' "$out/checksum.log" > /dev/null
echo 'PASS: existing work and symlinks preserved; corrupt source rejected before extraction'
