#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted real pinned development-toolchain export regression.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
[ "$#" -eq 1 ] || { echo 'Usage: prepare.sh ABSOLUTE_NEW_PKGSRC' >&2; exit 2; }
destination=$1
sh "$root/scripts/prepare-pkgsrc.sh" "$destination" development-toolchain
expected=$(git -C "$root" ls-files --stage -- upstream/pkgsrc | awk '$1 == "160000" {print $2}')
[ "$(cat "$destination/EMBERBSD-PKGSRC-REVISION")" = "$expected" ]
grep -q '^PKGREVISION=[[:space:]]*1$' "$destination/lang/gcc16/Makefile"
grep -q '^PKGREVISION=[[:space:]]*2$' "$destination/lang/gcc16-libs/Makefile"
for name in patch-gcc_testsuite_gcc.dg_vect_tsvc_tsvc.h patch-gcc_cp_module.cc; do
    recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name {print $4}' "$destination/lang/gcc16/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$destination/lang/gcc16/patches/$name" | shasum -a 1 | awk '{print $1}')
    [ -n "$recorded" ] && [ "$actual" = "$recorded" ] || { echo "Exported patch differs: $name" >&2; exit 1; }
done
echo 'PASS: real pinned development export, package revisions and retained TSVC/modules source payloads'
