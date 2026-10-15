#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Cross input guards without target compilation.
set -eu
[ "$#" = 5 ] || {
    echo 'Usage: cross-guards.sh GCC_PREFIX SYSROOT PCL_ARCHIVE GTEST_ARCHIVE NEW_RESULTS' >&2
    exit 2
}
compiler=$1 sysroot=$2 pcl=$3 gtest=$4 result=$5
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple absolute paths.' >&2; exit 2;; esac
done
[ ! -e "$result" ] && [ ! -L "$result" ] || { echo 'Results path already exists.' >&2; exit 2; }
[ -f "$pcl" ] && [ -f "$gtest" ] || { echo 'Original archives required.' >&2; exit 2; }
probe=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
mkdir -p "$result/preserved"
sha256sum "$pcl" "$gtest" > "$result/archive-inputs.sha256"
printf 'keep this file\n' > "$result/preserved/marker"
sha256sum "$result/preserved/marker" > "$result/marker.sha256"
printf 'invalid PCL source archive\n' > "$result/corrupt-pcl.tar.gz"
printf 'invalid GoogleTest source archive\n' > "$result/corrupt-gtest.tar.gz"
reject() {
    name=$1 expected=$2
    shift 2
    set +e
    (cd "$result" && "$@") > "$result/$name.log" 2>&1
    status=$?
    set -e
    printf '%s\n' "$status" > "$result/$name.status"
    [ "$status" = "$expected" ] || {
        echo "Unexpected $name status: $status (wanted $expected)" >&2; exit 1;
    }
}
for field in compiler sysroot pcl gtest output; do
    case "$field" in
        compiler) set -- relative-input "$sysroot" "$pcl" "$gtest" "$result/relative-output" ;;
        sysroot) set -- "$compiler" relative-input "$pcl" "$gtest" "$result/relative-output" ;;
        pcl) set -- "$compiler" "$sysroot" relative-input "$gtest" "$result/relative-output" ;;
        gtest) set -- "$compiler" "$sysroot" "$pcl" relative-input "$result/relative-output" ;;
        output) set -- "$compiler" "$sysroot" "$pcl" "$gtest" relative-output ;;
    esac
    reject "relative-$field" 2 sh "$probe/cross-build.sh" "$@"
    [ ! -e "$result/relative-output" ] && [ ! -L "$result/relative-output" ]
done
reject existing 2 sh "$probe/cross-build.sh" "$compiler" "$sysroot" "$pcl" "$gtest" "$result/preserved"
grep -Fx 'Output path already exists.' "$result/existing.log" >/dev/null
sha256sum -c "$result/marker.sha256" > "$result/marker-check.log"
ln -s preserved "$result/link"
reject symlink 2 sh "$probe/cross-build.sh" "$compiler" "$sysroot" "$pcl" "$gtest" "$result/link"
[ -L "$result/link" ] && [ "$(readlink "$result/link")" = preserved ]
sha256sum -c "$result/marker.sha256" >> "$result/marker-check.log"
reject zero-jobs 2 env CROSS_JOBS=00 sh "$probe/cross-build.sh" "$compiler" "$sysroot" "$pcl" "$gtest" "$result/jobs-output"
[ ! -e "$result/jobs-output" ] && [ ! -L "$result/jobs-output" ]
reject pcl-checksum 1 sh "$probe/cross-build.sh" "$compiler" "$sysroot" "$result/corrupt-pcl.tar.gz" "$gtest" "$result/pcl-output"
grep -F "$result/corrupt-pcl.tar.gz: FAILED" "$result/pcl-checksum.log" >/dev/null
[ ! -e "$result/pcl-output" ] && [ ! -L "$result/pcl-output" ]
reject gtest-checksum 1 sh "$probe/cross-build.sh" "$compiler" "$sysroot" "$pcl" "$result/corrupt-gtest.tar.gz" "$result/gtest-output"
grep -F "$pcl: OK" "$result/gtest-checksum.log" >/dev/null
grep -F "$result/corrupt-gtest.tar.gz: FAILED" "$result/gtest-checksum.log" >/dev/null
[ ! -e "$result/gtest-output" ] && [ ! -L "$result/gtest-output" ]
sha256sum -c "$result/archive-inputs.sha256" > "$result/archive-preservation.log"
echo 'PASS: five relative paths, existing directory, symlink, zero jobs, PCL and GoogleTest checksums before extraction'
