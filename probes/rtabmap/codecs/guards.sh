#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Reject invalid inputs before extraction.
set -eu
[ "$#" = 4 ] || { echo 'Usage: guards.sh GCC_PREFIX SYSROOT JPEG_RECIPE NEW_RESULTS' >&2; exit 2; }
compiler=$1 sysroot=$2 jpeg_recipe=$3 out=$4
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
mkdir -p "$out/preserved" "$out/archives"
printf 'keep\n' > "$out/preserved/marker"
printf 'corrupt source\n' > "$out/archives/libpng-1.6.59.tar.xz"
printf 'corrupt source\n' > "$out/archives/libjpeg-turbo-3.2.0.tar.gz"
reject()
{
    name=$1 expected=$2 destination=$3
    status=0
    sh "$recipe/build.sh" cross "$compiler" "$sysroot" /usr/pkg \
        "$out/archives" "$jpeg_recipe" "$destination" > "$out/$name.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$out/$name.status"
    [ "$status" = "$expected" ]
}
reject existing 2 "$out/preserved"
[ "$(cat "$out/preserved/marker")" = keep ]
ln -s "$out/preserved" "$out/link"
reject symlink 2 "$out/link"
[ -L "$out/link" ]
reject checksum 1 "$out/rejected"
[ ! -e "$out/rejected" ] && [ ! -L "$out/rejected" ]
grep 'FAILED' "$out/checksum.log" >/dev/null
echo 'PASS: existing work and symlinks preserved; corrupt source rejected before extraction'
