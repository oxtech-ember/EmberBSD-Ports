#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Reject invalid host-build inputs before work.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 VERIFIED_DISTFILES NEW_WORK" >&2; exit 2; }
distfiles=$1 work=$2
recipe=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/build-host-tools.sh
mkdir "$work"
reject() {
    name=$1; shift
    if "$@" > "$work/$name.log" 2>&1; then
        echo "Unexpected success: $name" >&2; exit 1
    fi
}
reject jobs env JOBS=0 sh "$recipe" "$distfiles" "$work/new"
grep -q 'JOBS must be positive' "$work/jobs.log"
reject relative sh "$recipe" "$distfiles" relative-output
grep -q 'Absolute paths required' "$work/relative.log"
reject missing env RESUME=1 sh "$recipe" "$distfiles" "$work/missing"
grep -q 'Cannot resume missing work' "$work/missing.log"
mkdir "$work/existing"
reject existing sh "$recipe" "$distfiles" "$work/existing"
grep -q 'Output already exists' "$work/existing.log"
ln -s "$work/existing" "$work/symlink"
reject symlink env RESUME=1 sh "$recipe" "$distfiles" "$work/symlink"
grep -q 'Output already exists' "$work/symlink.log"
: > "$work/existing/inputs.txt"
reject changed env RESUME=1 sh "$recipe" "$distfiles" "$work/existing"
grep -q 'Host input changed' "$work/changed.log"
mkdir "$work/archives"
for module in qtbase qtshadertools qtdeclarative; do
    ln -s "$distfiles/$module-everywhere-src-6.12.0.tar.xz" "$work/archives/"
done
printf 'corrupt archive\n' > "$work/archives/qttools-everywhere-src-6.12.0.tar.xz"
reject checksum sh "$recipe" "$work/archives" "$work/new"
grep -q 'Archive verification failed: qttools' "$work/checksum.log"
[ ! -e "$work/new" ] && [ ! -e "$work/missing" ]
printf '%s\n' 'PASS: invalid jobs/paths, missing/foreign resume, symlink and corrupt archive rejection'
