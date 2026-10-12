#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), evaluate the real cross recipe and dependencies.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 PKGSRC MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
: "${BMAKE:?Set the native BSD make executable}"
for path in "$pkgsrc" "$makeconf" "$work" "$BMAKE"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2 ;; esac
done
mkdir "$work"
query() { "$BMAKE" -C "$pkgsrc/lang/clang" MAKECONF="$makeconf" "$@"; }
query -V '${PKG_FAIL_REASON}' > "$work/valid.log"
[ -z "$(cat "$work/valid.log")" ]
query -V '${CCPATH}' > "$work/ccpath.log"
ccpath=$(cat "$work/ccpath.log")
case "$ccpath" in /*) ;; *) echo 'Compiler metadata needs an absolute executable' >&2; exit 1 ;; esac
[ -x "$ccpath" ]
[ "$("$ccpath" -dumpfullversion)" = 16.2.0 ]
query -V '${DEPENDS}' > "$work/depends.log"
grep -q 'perl>=5.44.0:../../lang/perl5' "$work/depends.log"
query -V '${REPLACE.target-perl.new}' > "$work/shebang.log"
[ "$(cat "$work/shebang.log")" = /usr/pkg/bin/perl ]
query -V '${TOOLS_PATH.perl}' > "$work/host-perl.log"
[ "$(cat "$work/host-perl.log")" != /usr/pkg/bin/perl ]
query -V '${CMAKE_CONFIGURE_ARGS}' > "$work/cmake.log"
grep -q -- '-DLLVM_INCLUDE_TESTS=ON' "$work/cmake.log"
grep -q -- '-DCLANG_INCLUDE_TESTS=ON' "$work/cmake.log"
grep -q -- '-DCLANG_ENABLE_HLSL=ON' "$work/cmake.log"
grep -q -- '-DLIBCLANG_BUILD_STATIC=ON' "$work/cmake.log"
for item in EMBERBSD_CLANG_TABLEGEN EMBERBSD_CROSS_BUILD_PERL; do
    query "$item=/nonexistent-ember-tool" -V '${PKG_FAIL_REASON}' > "$work/$item-missing.log" 2>&1
    grep -q 'must select\|Set EMBERBSD_CROSS_BUILD_PERL\|must execute' "$work/$item-missing.log"
    query "$item=/usr/bin/true" -V '${PKG_FAIL_REASON}' > "$work/$item-wrong.log" 2>&1
    grep -q 'must execute\|needs host Perl' "$work/$item-wrong.log"
done
echo 'PASS: real Clang recipe keeps target Perl, target shebangs and full test/static options'
