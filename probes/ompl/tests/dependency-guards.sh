#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), preflight rejection and output preservation.
set -eu
[ "$#" = 5 ] || { echo 'Usage: dependency-guards.sh GCC_PREFIX SYSROOT EIGEN_ARCHIVE BOOST_ARCHIVE NEW_WORK' >&2; exit 2; }
compiler=$1 sysroot=$2 eigen=$3 boost=$4 work=$5
case "$work" in /*) ;; *) exit 2;; esac
[ ! -e "$work" ] && [ ! -L "$work" ] || exit 2
ports=$(CDPATH= cd "$(dirname "$0")/../../.." && pwd -P)
helper=$ports/probes/ompl/cross/build-dependencies.sh
mkdir -p "$work/logs"
reject()
{
    name=$1; shift
    status=0
    "$@" > "$work/logs/$name.log" 2>&1 || status=$?
    [ "$status" -ne 0 ] || { echo "Accepted invalid input: $name" >&2; exit 1; }
    [ ! -e "$work/output" ] && [ ! -L "$work/output" ] || exit 1
    printf '%s %s\n' "$name" "$status" >> "$work/statuses.txt"
}
for jobs in 0 00 invalid -1; do
    reject "jobs-$jobs" env CROSS_JOBS="$jobs" "$helper" "$compiler" "$sysroot" "$eigen" "$boost" "$work/output"
    grep -F 'CROSS_JOBS must be positive.' "$work/logs/jobs-$jobs.log" >/dev/null
done
fixture=$work/ports
mkdir -p "$fixture/probes/ompl/cross" "$fixture/pkgsrc/local-robotics"
cp "$helper" "$fixture/probes/ompl/cross/"
for package in eigen3 boost-headers boost-libs; do
    cp -R "$ports/pkgsrc/local-robotics/$package" "$fixture/pkgsrc/local-robotics/"
done
for package in eigen3 boost-headers boost-libs; do
    mv "$fixture/pkgsrc/local-robotics/$package/PLIST" "$work/PLIST.saved"
    reject "missing-$package-plist" "$fixture/probes/ompl/cross/build-dependencies.sh" "$compiler" "$sysroot" "$eigen" "$boost" "$work/output"
    grep -F "Missing $package package metadata: PLIST" "$work/logs/missing-$package-plist.log" >/dev/null
    mv "$work/PLIST.saved" "$fixture/pkgsrc/local-robotics/$package/PLIST"
done
printf 'Invalid archive control\n' > "$work/bad-archive.tar"
reject invalid-archive "$helper" "$compiler" "$sysroot" "$work/bad-archive.tar" "$boost" "$work/output"
grep -F 'FAILED' "$work/logs/invalid-archive.log" >/dev/null
mkdir "$work/preserved"
printf 'Keep existing output\n' > "$work/preserved/marker"
cp "$work/preserved/marker" "$work/expected-marker"
reject existing-output "$helper" "$compiler" "$sysroot" "$eigen" "$boost" "$work/preserved"
cmp "$work/preserved/marker" "$work/expected-marker"
echo 'PASS dependency preflight guards and existing output preservation'
