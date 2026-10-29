#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Exercise the real late compiler policy with bmake and explicit language cases.
set -eu
[ "$#" = 3 ] || { echo 'usage: cxx-runtime-policy.sh BMAKE POLICY PKGSRC' >&2; exit 2; }
bmake=$1 policy=$2 pkgsrc=$3
case_test() {
 expected=$1; shift
 out=$("$bmake" -f "$policy" "$@" -V '${DEPENDS}' -V '${BUILD_DEPENDS}')
 case "$expected:$out" in yes:*libcxx-devel*libunwind-devel*) ;; no:*libcxx*|yes:*) echo "wrong policy: $* $out" >&2; exit 1;; no:*) ;; esac
}
base='TOOLS_USE_CROSS_COMPILE=yes EMBERBSD_CROSS_COMPILER_FAMILY=clang PKGSRC_COMPILER=clang _EMBER_TARGET_RUNTIME_VERSION=23.1.4 _EMBER_TARGET_RUNTIME_KIND=stage _EMBER_TARGET_RUNTIME_ROOT=/stage _EMBER_TARGET_RUNTIME_BASE=/base _EMBER_TARGET_SDK_SOURCE=/sdk _EMBER_TARGET_NATIVE_PYTHON=/python'
# Intentional splitting: each fixed assignment is one bmake argument.
# shellcheck disable=SC2086
case_test yes PKGSRCDIR="$pkgsrc" $base PKGPATH=local/cxx 'USE_LANGUAGES=c c++'
# shellcheck disable=SC2086
case_test no PKGSRCDIR="$pkgsrc" $base PKGPATH=local/c USE_LANGUAGES=c
# shellcheck disable=SC2086
case_test no PKGSRCDIR="$pkgsrc" $base PKGPATH=lang/compiler-rt 'USE_LANGUAGES=c c++'
# shellcheck disable=SC2086
case_test no PKGSRCDIR="$pkgsrc" $base PKGPATH=lang/libcxx 'USE_LANGUAGES=c c++'
case_test no TOOLS_USE_CROSS_COMPILE=no EMBERBSD_HOST_COMPILER_FAMILY=clang PKGSRC_COMPILER=clang PKGPATH=local/cxx 'USE_LANGUAGES=c c++'
case_test no TOOLS_USE_CROSS_COMPILE=yes EMBERBSD_CROSS_COMPILER_FAMILY=gcc PKGSRC_COMPILER=gcc PKGPATH=local/cxx 'USE_LANGUAGES=c c++'
echo 'PASS: C, C++, native, GCC, producer and provider policy'
