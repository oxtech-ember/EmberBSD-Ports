#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Preserve inputs before extraction or compilation.
set -eu
[ "$#" = 4 ] || {
    echo 'Usage: input-guards.sh GCC_PREFIX SYSROOT SQLITE_ARCHIVE NEW_RESULTS' >&2
    exit 2
}
compiler=$1 sysroot=$2 archive=$3 result=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple absolute paths.' >&2; exit 2;; esac
done
[ ! -e "$result" ] && [ ! -L "$result" ] || exit 2
probe=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
mkdir -p "$result/preserved" "$result/prefix"
printf 'preserve\n' > "$result/preserved/marker"
printf 'corrupt SQLite archive\n' > "$result/corrupt.tar.gz"
sha256sum "$archive" "$result/preserved/marker" > "$result/inputs.sha256"
reject() {
    name=$1 expected=$2
    shift 2
    status=0
    "$@" > "$result/$name.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$result/$name.status"
    [ "$status" = "$expected" ] || { echo "Unexpected $name status: $status" >&2; exit 1; }
}
reject cross-existing 2 sh "$probe/build.sh" --cross "$compiler" "$sysroot" "$archive" "$result/preserved"
grep -F 'Output path already exists' "$result/cross-existing.log" >/dev/null
reject native-existing 2 sh "$probe/build.sh" --native "$result/prefix" "$archive" "$result/preserved"
ln -s preserved "$result/link"
reject symlink 2 sh "$probe/build.sh" --native "$result/prefix" "$archive" "$result/link"
[ -L "$result/link" ] && [ "$(readlink "$result/link")" = preserved ]
reject jobs 2 env JOBS=00 sh "$probe/build.sh" --native "$result/prefix" "$archive" "$result/jobs-output"
[ ! -e "$result/jobs-output" ] && [ ! -L "$result/jobs-output" ]
reject corrupt 1 sh "$probe/build.sh" --cross "$compiler" "$sysroot" "$result/corrupt.tar.gz" "$result/corrupt-output"
grep -F "$result/corrupt.tar.gz: FAILED" "$result/corrupt.log" >/dev/null
[ ! -e "$result/corrupt-output" ] && [ ! -L "$result/corrupt-output" ]
reject relative 2 sh "$probe/build.sh" --cross relative-compiler "$sysroot" "$archive" "$result/relative-output"
[ ! -e "$result/relative-output" ] && [ ! -L "$result/relative-output" ]
reject consumer-existing 2 sh "$probe/check.sh" --native "$result/prefix" "$result/preserved"
reject consumer-symlink 2 sh "$probe/check.sh" --cross "$compiler" "$sysroot" "$result/prefix" "$result/link"
sha256sum -c "$result/inputs.sha256" > "$result/preservation.log"
echo 'PASS native/cross output guards, symlinks, zero jobs, archive hash and relative input'
