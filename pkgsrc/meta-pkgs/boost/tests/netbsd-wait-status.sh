#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake netbsd-wait-status.sh PKGSRC MAKECONF
#
# boost/process/v2/exit_code.hpp checks its still_active status with
# static_assert on the <sys/wait.h> macros. NetBSD's macros read the status
# through *(int *)(void *)&(w), which is not a constant expression, so a
# NetBSD target build of Boost.Process stopped with "static assertion
# expression is not an integral constant expression". Patch the Boost
# sources as the recipe does and compile the header for the target.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/devel/boost-headers makeconf=$2
# pkgsrc wants a canonical WRKDIR.
work=$(cd "$(mktemp -d "${TMPDIR:-/tmp}/boost-wait.XXXXXX")" && pwd -P)
trap 'rm -rf "$work"' EXIT
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" \
	WRKOBJDIR="$work/objects" SKIP_DEPENDS=yes "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] && [ "$(bm -V '${OPSYS}')" = NetBSD ] ||
	{ echo "$0: select a MAKECONF for a NetBSD cross build" >&2; exit 2; }
src=$(bm -V '${WRKSRC}')
cxx=$(bm -V '${TOOLDIR}')/bin/$(bm -V '${CXX}')
bm patch >"$work/patch.log" 2>&1 || { cat "$work/patch.log"; echo "FAIL: patch"; exit 1; }
printf '#include <boost/process/v2/exit_code.hpp>\n' >"$work/t.cc"
status=0
for std in c++11 c++14 c++17; do
	"$cxx" -std=$std -fsyntax-only -I"$src" "$work/t.cc" >"$work/cc.log" 2>&1 ||
		{ grep 'error:' "$work/cc.log" | sed 1q; echo "FAIL: -std=$std"; status=1; }
done
[ "$status" -eq 0 ] || exit 1
echo "PASS: boost/process/v2/exit_code.hpp compiles for the NetBSD target"
