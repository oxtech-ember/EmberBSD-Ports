#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check rejection before extraction or overwrite.
set -eu
[ "$#" = 5 ] || { echo 'Usage: test-dependency-guards.sh GCC_PREFIX SYSROOT FLANN_ARCHIVE LZ4_ARCHIVE NEW_RESULTS' >&2; exit 2; }
compiler=$1 sysroot=$2 flann=$3 lz4=$4 results=$5
[ ! -e "$results" ] && [ ! -L "$results" ] || exit 2
mkdir -p "$results"
cross=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
reject()
{
    name=$1; shift
    status=0
    "$@" > "$results/$name.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$results/$name.status"
    [ "$status" -ne 0 ] || { echo "Accepted invalid input: $name" >&2; exit 1; }
}
printf 'corrupt archive\n' > "$results/corrupt.tar.xz"
reject corrupt-source sh "$cross/build-dependencies.sh" "$compiler" "$sysroot" "$results/corrupt.tar.xz" "$lz4" "$results/corrupt-output"
[ ! -e "$results/corrupt-output" ] && [ ! -L "$results/corrupt-output" ]
mkdir "$results/existing-output"
printf 'preserve\n' > "$results/existing-output/sentinel"
reject existing-output sh "$cross/build-dependencies.sh" "$compiler" "$sysroot" "$flann" "$lz4" "$results/existing-output"
[ "$(cat "$results/existing-output/sentinel")" = preserve ]
ln -s existing-output "$results/symlink-output"
reject symlink-output sh "$cross/build-dependencies.sh" "$compiler" "$sysroot" "$flann" "$lz4" "$results/symlink-output"
[ -L "$results/symlink-output" ]
[ "$(cat "$results/symlink-output/sentinel")" = preserve ]
reject zero-jobs env CROSS_JOBS=00 sh "$cross/build-dependencies.sh" "$compiler" "$sysroot" "$flann" "$lz4" "$results/zero-output"
[ ! -e "$results/zero-output" ] && [ ! -L "$results/zero-output" ]
mkdir -p "$results/import-source" "$results/import-destination"
printf 'new\n' > "$results/import-source/a-new"
printf 'replacement\n' > "$results/import-source/z-existing"
printf 'preserve\n' > "$results/import-destination/z-existing"
reject import-collision ruby "$cross/import-stage.rb" "$results/import-source" "$results/import-destination"
[ ! -e "$results/import-destination/a-new" ]
[ "$(cat "$results/import-destination/z-existing")" = preserve ]
printf 'preserve\n' > "$results/import-source/z-existing"
ruby "$cross/import-stage.rb" "$results/import-source" "$results/import-destination" > "$results/import-identical.log"
cmp "$results/import-source/a-new" "$results/import-destination/a-new"
cmp "$results/import-source/z-existing" "$results/import-destination/z-existing"
mkdir -p "$results/symlink-source/redirect" "$results/symlink-destination" "$results/outside"
printf 'preserve\n' > "$results/outside/sentinel"
printf 'replacement\n' > "$results/symlink-source/redirect/sentinel"
ln -s ../outside "$results/symlink-destination/redirect"
reject import-symlink-parent ruby "$cross/import-stage.rb" "$results/symlink-source" "$results/symlink-destination"
[ "$(cat "$results/outside/sentinel")" = preserve ]
echo 'PASS source, output, jobs and collision guards'
