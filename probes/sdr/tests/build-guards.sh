#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 1 ] || { echo 'Usage: build-guards.sh ABS_NEW_WORK' >&2; exit 2; }
root=$1
case "$root" in /*) ;; *) exit 2 ;; esac
[ ! -e "$root" ] || exit 2
mkdir "$root"
recipe=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
[ -n "${XML_PREFIX:-}" ] || { echo 'Set XML_PREFIX to the tested common provider.' >&2; exit 2; }
expect_failure() {
    name=$1; shift
    code=0
    "$@" > "$root/$name.log" 2>&1 || code=$?
    [ "$code" -ne 0 ] || { echo "FAIL: $name unexpectedly succeeded" >&2; exit 1; }
}
expect_failure relative "$recipe/build.sh" relative
expect_failure existing "$recipe/build.sh" "$root"
expect_failure missing-xml env -u XML_PREFIX "$recipe/build.sh" "$root/missing-xml"
grep -q 'Set XML_PREFIX' "$root/missing-xml.log"
expect_failure jobs env HOST_CHECK=1 JOBS=0 "$recipe/build.sh" "$root/jobs"
expect_failure limit env HOST_CHECK=1 BUILD_AS_KIB=invalid "$recipe/build.sh" "$root/limit"
[ ! -e "$root/jobs" ] && [ ! -e "$root/limit" ] || exit 1
mkdir "$root/cache"
printf 'intentionally corrupt\n' > "$root/cache/SoapySDR-0.8.1.tar.gz"
expect_failure archive env HOST_CHECK=1 "$recipe/build.sh" "$root/archive" "$root/cache"
grep -q 'Source checksum mismatch' "$root/archive.log"
cp -R "$recipe" "$root/recipe"
mkdir -p "$root/libxml2"
cp "$recipe/../libxml2/sources.tsv" "$root/libxml2/sources.tsv"
printf '\ncorruption\n' >> "$root/recipe/patches/pluto-explicit-context.patch"
expect_failure patch env HOST_CHECK=1 "$root/recipe/build.sh" "$root/patch" "$root/cache"
grep -q 'Patch checksum mismatch' "$root/patch.log"
[ ! -e "$root/patch" ] || exit 1
expect_failure missing-install "$recipe/test.sh" "$root"
echo 'PASS path, existing-work, jobs, explicit memory limit, archive, patch and installed-inventory guards'
