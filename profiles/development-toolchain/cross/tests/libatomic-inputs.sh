#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted cross helper input-preservation regression.
set -eu
[ "$#" -eq 4 ] || {
    echo 'Usage: libatomic-inputs.sh GCC_PREFIX SYSROOT GCC_ARCHIVE NEW_RESULTS' >&2
    exit 2
}
compiler=$1 sysroot=$2 archive=$3 result=$4
case "$result" in /*) ;; *) echo 'Absolute NEW_RESULTS required.' >&2; exit 2;; esac
[ ! -e "$result" ] && [ ! -L "$result" ] || {
    echo 'NEW_RESULTS already exists.' >&2; exit 2;
}
helper=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)/build-libatomic.sh
mkdir -p "$result"
expect_failure() {
    expected=$1 name=$2
    shift 2
    set +e
    "$@" > "$result/$name.log" 2>&1
    status=$?
    set -e
    printf '%s\n' "$status" > "$result/$name.status"
    [ "$status" -eq "$expected" ] || {
        echo "Unexpected status for $name: $status" >&2; exit 1;
    }
}
mkdir "$result/existing"
printf 'preserve\n' > "$result/existing/sentinel"
expect_failure 2 existing sh "$helper" "$compiler" "$sysroot" "$archive" "$result/existing"
[ "$(cat "$result/existing/sentinel")" = preserve ]
ln -s existing "$result/link"
expect_failure 2 symlink sh "$helper" "$compiler" "$sysroot" "$archive" "$result/link"
[ -L "$result/link" ] && [ "$(cat "$result/link/sentinel")" = preserve ]
printf 'invalid GCC archive\n' > "$result/corrupt.tar.xz"
expect_failure 1 corrupt sh "$helper" "$compiler" "$sysroot" "$result/corrupt.tar.xz" "$result/corrupt-output"
[ ! -e "$result/corrupt-output" ] && [ ! -L "$result/corrupt-output" ]
expect_failure 2 jobs env CROSS_JOBS=0 sh "$helper" "$compiler" "$sysroot" "$archive" "$result/jobs-output"
[ ! -e "$result/jobs-output" ] && [ ! -L "$result/jobs-output" ]
printf 'PASS existing directory, symlink, corrupt archive, invalid worker count\n'
