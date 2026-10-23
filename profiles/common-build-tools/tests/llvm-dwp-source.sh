#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), canonical DWP patch/checksum regression.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 VERIFIED_LLVM_ARCHIVE NEW_WORK" >&2; exit 2; }
archive=$1 work=$2
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
recipe=$root/pkgsrc/lang/llvm
patch=$recipe/patches/patch-lib_DWP_DWP.cpp
mkdir "$work"
work=$(CDPATH= cd -- "$work" && pwd)
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = \
    c44186a7762ed28954be72e5ff6df9808e0779d4f1bf014ecc4e7e211d31ee34 ]
expected=$(awk '/^SHA1 \(patch-lib_DWP_DWP.cpp\)/ { print $4 }' "$recipe/distinfo")
actual=$(sed '/[$]NetBSD.*/d' "$patch" | shasum -a 1 | awk '{print $1}')
[ "$expected" = "$actual" ]
tar -xf "$archive" -C "$work" llvm-project-23.1.3.src/llvm/lib/DWP/DWP.cpp
tree=$work/llvm-project-23.1.3.src/llvm
cp "$tree/lib/DWP/DWP.cpp" "$work/DWP.cpp.orig"
patch -f -N -F 0 -p0 -d "$tree" < "$patch" > "$work/forward.log"
if patch -f -N -F 0 -p0 -d "$tree" < "$patch" > "$work/repeated.log" 2>&1; then
    echo 'FAIL: repeated DWP patch accepted' >&2
    exit 1
fi
[ ! -e "$root/profiles/development-toolchain/gdb/dwarf-variants-llvm-dwp.patch" ]
[ ! -e "$root/profiles/development-toolchain/gdb/dwarf-variants-dwp-build.sh" ]
grep -q '^LLVM_VERSION=.*23\.1\.3$' "$recipe/version.mk"
echo 'PASS: pinned source, patch hash, zero-fuzz application, repeated rejection and single recipe ownership'
