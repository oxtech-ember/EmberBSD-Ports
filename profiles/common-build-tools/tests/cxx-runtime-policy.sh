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
base='USE_CROSS_COMPILE=yes TOOLS_USE_CROSS_COMPILE=yes EMBERBSD_CROSS_COMPILER_FAMILY=clang PKGSRC_COMPILER=clang _EMBER_TARGET_RUNTIME_VERSION=23.1.4 _EMBER_TARGET_RUNTIME_KIND=stage _EMBER_TARGET_RUNTIME_ROOT=/stage _EMBER_TARGET_RUNTIME_BASE=/base _EMBER_TARGET_SDK_SOURCE=/sdk _EMBER_TARGET_NATIVE_PYTHON=/python'
# Intentional splitting: each fixed assignment is one bmake argument.
# shellcheck disable=SC2086
# shellcheck disable=SC2086
case_test no PKGSRCDIR="$pkgsrc" $base PKGPATH=lang/compiler-rt 'USE_LANGUAGES=c c++'
# shellcheck disable=SC2086
case_test no PKGSRCDIR="$pkgsrc" $base PKGPATH=lang/libcxx 'USE_LANGUAGES=c c++'
case_test no TOOLS_USE_CROSS_COMPILE=no EMBERBSD_HOST_COMPILER_FAMILY=clang PKGSRC_COMPILER=clang PKGPATH=local/cxx 'USE_LANGUAGES=c c++'
case_test no TOOLS_USE_CROSS_COMPILE=yes EMBERBSD_CROSS_COMPILER_FAMILY=gcc PKGSRC_COMPILER=gcc PKGPATH=local/cxx 'USE_LANGUAGES=c c++'
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-cxx-runtime-policy.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
language_case() {
	name=$1 runtime_kind=$2 languages=$3
	cat >"$work/$name.mk" <<EOF
PKGSRCDIR=$pkgsrc
TOOLS_USE_CROSS_COMPILE=yes
USE_CROSS_COMPILE=yes
EMBERBSD_CROSS_COMPILER_FAMILY=clang
PKGSRC_COMPILER=clang
_EMBER_TARGET_RUNTIME_VERSION=23.1.4
_EMBER_TARGET_RUNTIME_KIND=$runtime_kind
_EMBER_TARGET_RUNTIME_ROOT=/runtime
_EMBER_TARGET_RUNTIME_BASE=/base
_EMBER_TARGET_SDK_SOURCE=/sdk
_EMBER_TARGET_NATIVE_PYTHON=/python
PKGPATH=local/$name
USE_LANGUAGES= $languages
.include "$policy"
EOF
	"$bmake" -f "$work/$name.mk" -V DEPENDS -V BUILD_DEPENDS -V PKG_FAIL_REASON
}
full=$(language_case full stage 'c c++')
case "$full" in *libcxx-devel*libunwind-devel*) ;; *) echo "full runtime lost C++ closure: $full" >&2; exit 1;; esac
for language in c++11 c++17 gnu++17 obj-c++ ; do
	full=$(language_case "full-$language" stage "c $language")
	case "$full" in *libcxx-devel*libunwind-devel*) ;; *) echo "full runtime lost $language closure: $full" >&2; exit 1;; esac
done
c_only=$(language_case c-only c-only c)
case "$c_only" in *libcxx*|*C\ support\ only*) echo "C-only route selected C++ inputs: $c_only" >&2; exit 1;; esac
asm=$(language_case c-asm c-only 'c asm')
case "$asm" in *libcxx*|*"supports only"*) echo "C-only route rejected C/ASM: $asm" >&2; exit 1;; esac
for language in c99 gnu99 c11 gnu11 c17 gnu17 ; do
	c_dialect=$(language_case "c-$language" c-only "c $language")
	case "$c_dialect" in *libcxx*|*"supports only"*) echo "C-only route rejected C dialect $language: $c_dialect" >&2; exit 1;; esac
done
data=$(language_case data-only c-only '')
case "$data" in *libcxx*|*"supports only"*) echo "C-only route rejected data-only package: $data" >&2; exit 1;; esac
for language in c++ c++11 c++17 gnu++17 objc obj-c++ fortran ada ; do
	reason=$(language_case "reject-$language" c-only "c $language")
	case "$reason" in *"supports only C and assembly"*) ;; *) echo "C-only runtime accepted $language package: $reason" >&2; exit 1;; esac
done
echo 'PASS: C, C++, native, GCC, producer and provider policy'
