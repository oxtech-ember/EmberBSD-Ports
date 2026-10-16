#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; verify failures before a long cross-compiler build starts.
set -eu
usage() { echo 'Usage: test-inputs.sh [--target aarch64|amd64] EXPORTED_PKGSRC GCC_ARCHIVE SYSROOT TOOLDIR [HOST_MATH_PREFIX]' >&2; exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
. "$here/target-options.sh"
[ "$#" -eq 4 ] || [ "$#" -eq 5 ] || usage
tree=$1 archive=$2 sysroot=$3 tools=$4 math=${5:-}
build() { sh "$here/build.sh" --target "$target" "$@"; }
work=$(mktemp -d "${TMPDIR:-/tmp}/gcc16-cross-inputs.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
reject() {
    name=$1 expected=$2; shift 2
    [ -z "$math" ] || set -- "$@" "$math"
    if build "$@" "$work/$name-output" > "$work/$name.log" 2>&1; then
        echo "Accepted invalid input: $name" >&2; exit 1
    fi
    grep -F "$expected" "$work/$name.log" >/dev/null
    test ! -e "$work/$name-output"
}
printf corrupt > "$work/archive.tar.xz"
reject archive 'GCC archive SHA256 mismatch' "$tree" "$work/archive.tar.xz" "$sysroot" "$tools"
mkdir -p "$work/tree/lang/gcc16"
cp "$tree/lang/gcc16/distinfo" "$work/tree/lang/gcc16/"
cp -R "$tree/lang/gcc16/patches" "$work/tree/lang/gcc16/"
printf '\ncorrupt\n' >> "$work/tree/lang/gcc16/patches/patch-gcc_cp_module.cc"
reject patch 'Patch SHA1 mismatch: patch-gcc_cp_module.cc' "$work/tree" "$archive" "$sysroot" "$tools"
rm "$work/tree/lang/gcc16/patches/patch-gcc_cp_module.cc"
reject missing 'Missing patch: patch-gcc_cp_module.cc' "$work/tree" "$archive" "$sysroot" "$tools"
(CROSS_JOBS=0 reject jobs 'CROSS_JOBS must be positive' "$tree" "$archive" "$sysroot" "$tools")
(CROSS_JOBS=00 reject zeroes 'CROSS_JOBS must be positive' "$tree" "$work/archive.tar.xz" "$sysroot" "$tools")
mkdir -p "$work/old-math/lib" "$work/old-math/include"
for library in gmp mpfr mpc; do
    : > "$work/old-math/lib/lib$library.a"
done
printf '#define __GNU_MP_VERSION 6\n#define __GNU_MP_VERSION_MINOR 2\n#define __GNU_MP_VERSION_PATCHLEVEL 1\n' > "$work/old-math/include/gmp.h"
if build "$tree" "$archive" "$sysroot" "$tools" \
    "$work/old-math" "$work/old-math-output" > "$work/old-math.log" 2>&1; then
    echo 'Accepted unsupported old host GMP.' >&2; exit 1
fi
grep -F 'Host GMP 6.3.0 is required' "$work/old-math.log" >/dev/null
test ! -e "$work/old-math-output"
mkdir "$work/host-archives"
printf corrupt > "$work/host-archives/gmp-6.3.0.tar.xz"
if (
    unset EMBER_HOST_MATH_PREFIX
    EMBER_HOST_MATH_ARCHIVES=$work/host-archives build \
        "$tree" "$archive" "$sysroot" "$tools" "$work/automatic-math-output"
) > "$work/automatic-math.log" 2>&1; then
    echo 'Accepted corrupt automatic host prerequisite.' >&2; exit 1
fi
grep -F 'gmp archive SHA256 mismatch' "$work/automatic-math.log" >/dev/null
test ! -e "$work/automatic-math-output/src"
test ! -e "$work/automatic-math-output/host-math"
echo 'PASS: corrupt inputs and old GMP rejected; legacy CLI selects automatic host prerequisites'
