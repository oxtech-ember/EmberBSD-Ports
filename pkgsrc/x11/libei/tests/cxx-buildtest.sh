#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cxx-buildtest.sh PKGSRC MAKECONF
#
# test/buildtest.cc ends with "using namespace std;", but the libei headers
# declare nothing in std. clang then reports a using-directive for an
# implicitly-defined namespace, and the -Werror from patch-test_meson.build
# stopped the build. Patch the recipe and compile both header checks with
# the recipe's target C++ compiler and the flags Meson uses.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/x11/libei makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" SKIP_DEPENDS=yes "$@"; }
src=$(bm -V '${WRKSRC}') sysroot=$(bm -V '${CROSS_DESTDIR:U}')
if [ -n "$sysroot" ]; then cxx=$(bm -V '${TOOLDIR}/bin/${CXX}'); else cxx=$(bm -V '${CXX}'); fi
trap 'bm clean >/dev/null 2>&1 || :' EXIT
bm clean >/dev/null 2>&1 || :
bm patch >/dev/null 2>&1 || { echo "FAIL: patch"; exit 1; }
status=0
for macro in INCLUDE_LIBEI INCLUDE_LIBEIS; do
	"$cxx" ${sysroot:+--sysroot="$sysroot"} -Wall -Wextra -Werror -D$macro=1 \
	    -I"$src/src" -fsyntax-only "$src/test/buildtest.cc" ||
		{ echo "FAIL: buildtest.cc with $macro"; status=1; }
done
[ "$status" -eq 0 ] || exit 1
echo "PASS: libei C++ header checks compile with -Werror"
