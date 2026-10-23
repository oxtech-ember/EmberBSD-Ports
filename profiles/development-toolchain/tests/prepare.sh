#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted real pinned development-toolchain export regression.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
[ "$#" -eq 1 ] || { echo 'Usage: prepare.sh ABSOLUTE_NEW_PKGSRC' >&2; exit 2; }
destination=$1
sh "$root/scripts/prepare-pkgsrc.sh" "$destination"
expected=$(git -C "$root" ls-files --stage -- upstream/pkgsrc | awk '$1 == "160000" {print $2}')
[ "$(cat "$destination/EMBERBSD-PKGSRC-REVISION")" = "$expected" ]
grep -q '^PKGREVISION=[[:space:]]*4$' "$destination/lang/gcc16/Makefile"
grep -q '^PKGREVISION=[[:space:]]*5$' "$destination/lang/gcc16-libs/Makefile"
for name in patch-gcc_testsuite_gcc.dg_vect_tsvc_tsvc.h patch-gcc_cp_module.cc; do
    recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name {print $4}' "$destination/lang/gcc16/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$destination/lang/gcc16/patches/$name" | shasum -a 1 | awk '{print $1}')
    [ -n "$recorded" ] && [ "$actual" = "$recorded" ] || { echo "Exported patch differs: $name" >&2; exit 1; }
done
for name in Makefile PLIST DESCR files/runtime.py files/inheritance.py files/relro.py files/sdk_source.py files/tls_abi.py; do
    cmp "$root/profiles/development-toolchain/runtime/recipe/$name" "$destination/lang/gcc16-runtime/$name"
done
for name in runtime inheritance relro; do
    [ ! -e "$destination/lang/gcc16-runtime/files/$name.rb" ]
done
grep -q 'GCC16_RUNTIME_PYTHON' "$destination/lang/gcc16-runtime/Makefile"
grep -q 'EMBERBSD_SDK_SOURCE' "$destination/lang/gcc16-runtime/Makefile"
echo 'PASS: pinned development export, current revisions, source payloads and Python runtime recipe'
