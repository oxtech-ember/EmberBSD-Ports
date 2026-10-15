#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Portable guards; no native compilation needed.
set -eu
[ "$#" = 1 ] || { echo 'Usage: build-guards.sh ABS_NEW_RESULTS' >&2; exit 2; }
result=$1
case "$result" in /*) ;; *) echo 'Use an absolute results path.' >&2; exit 2;; esac
case "$result" in *[!A-Za-z0-9_./-]*) echo 'Use a simple results path.' >&2; exit 2;; esac
[ ! -e "$result" ] && [ ! -L "$result" ] || { echo 'Results path already exists.' >&2; exit 2; }
probe=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
mkdir -p "$result/cache" "$result/common" "$result/existing"
expect_failure() {
    name=$1 message=$2
    shift 2
    set +e
    "$@" > "$result/$name.log" 2>&1
    status=$?
    set -e
    printf '%s\n' "$status" > "$result/$name.status"
    [ "$status" = 2 ] || { echo "Unexpected $name status: $status" >&2; exit 1; }
    grep -F "$message" "$result/$name.log" >/dev/null
}
printf 'preserve\n' > "$result/existing/sentinel"
expect_failure existing 'Work path already exists' sh "$probe/build.sh" "$result/common" "$result/existing"
[ "$(cat "$result/existing/sentinel")" = preserve ]
ln -s existing "$result/link"
expect_failure symlink 'Work path already exists' sh "$probe/build.sh" "$result/common" "$result/link"
[ -L "$result/link" ] && [ "$(cat "$result/link/sentinel")" = preserve ]
for jobs in 0 00; do
    expect_failure "jobs-$jobs" 'JOBS must be positive' env JOBS="$jobs" \
        sh "$probe/build.sh" "$result/common" "$result/jobs-$jobs-output"
    [ ! -e "$result/jobs-$jobs-output" ] && [ ! -L "$result/jobs-$jobs-output" ]
done
for limit in 0 unlimited; do
    expect_failure "limit-$limit" 'BUILD_AS_KIB must be positive' env BUILD_AS_KIB="$limit" \
        sh "$probe/build.sh" "$result/common" "$result/limit-$limit-output"
    [ ! -e "$result/limit-$limit-output" ] && [ ! -L "$result/limit-$limit-output" ]
done
while read -r name expected url; do
    [ -n "$name" ] || continue
    printf 'corrupt archive\n' > "$result/cache/$name"
done < "$probe/sources.tsv"
expect_failure corrupt 'Checksum mismatch' sh "$probe/build.sh" "$result/common" "$result/corrupt-output" "$result/cache"
[ -z "$(find "$result/corrupt-output/source" -mindepth 1 -print)" ]
printf 'PASS existing directory, symlink, zero worker counts, invalid limits, corrupt archive before extraction\n'
