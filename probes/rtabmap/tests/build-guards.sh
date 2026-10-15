#!/bin/sh
# SPDX-License-Identifier: MIT
# Portable source/input guards; no compilation or target OS is required.
set -eu
[ "$#" = 1 ] || { echo 'Usage: build-guards.sh ABS_SCRATCH_PARENT' >&2; exit 2; }
case "$1" in /*) ;; *) exit 2 ;; esac
recipe=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
scratch=$(mktemp -d "$1/probe-guards.XXXXXX")
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
mkdir "$scratch/cache" "$scratch/existing" "$scratch/common"
printf 'preserve\n' > "$scratch/existing/sentinel"
if sh "$recipe/build.sh" "$scratch/common" "$scratch/existing" > "$scratch/existing.log" 2>&1; then exit 1; fi
grep -q 'Work path already exists' "$scratch/existing.log"
[ "$(cat "$scratch/existing/sentinel")" = preserve ]
if JOBS=0 sh "$recipe/build.sh" "$scratch/common" "$scratch/jobs" > "$scratch/jobs.log" 2>&1; then exit 1; fi
grep -q 'JOBS must be positive' "$scratch/jobs.log"
[ ! -e "$scratch/jobs" ]
if BUILD_AS_KIB=0 sh "$recipe/build.sh" "$scratch/common" "$scratch/as-zero" > "$scratch/as-zero.log" 2>&1; then exit 1; fi
grep -q 'BUILD_AS_KIB must be positive' "$scratch/as-zero.log"
[ ! -e "$scratch/as-zero" ]
if BUILD_AS_KIB=unlimited sh "$recipe/build.sh" "$scratch/common" "$scratch/as-unlimited" > "$scratch/as-unlimited.log" 2>&1; then exit 1; fi
grep -q 'BUILD_AS_KIB must be positive' "$scratch/as-unlimited.log"
[ ! -e "$scratch/as-unlimited" ]
while read -r name expected url; do printf 'corrupt\n' > "$scratch/cache/$name"; done < "$recipe/sources.tsv"
if sh "$recipe/build.sh" "$scratch/common" "$scratch/corrupt" "$scratch/cache" > "$scratch/corrupt.log" 2>&1; then exit 1; fi
grep -q 'Checksum mismatch' "$scratch/corrupt.log"
[ -z "$(ls -A "$scratch/corrupt/source")" ]
echo 'PASS existing work, zero jobs, invalid address-space limits, and corrupt archive rejected before extraction'
