#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake py-kiwisolver-cross-cppy-headers.sh PKGSRC MAKECONF
#
# kiwisolver's setup.py imports cppy with the build tool Python and adds the
# include directory of that cppy, which is outside the target buildlink tree.
# The cross wrapper drops it, and the cross build stopped with "'cppy/cppy.h'
# file not found". Check that the cross build of math/py-kiwisolver keeps cppy
# as a tool dependency, buildlinks the target cppy and adds its headers from
# the buildlink tree.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
bm() {
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/math/py-kiwisolver" \
	    MAKECONF="$makeconf" "$@" </dev/null 2>/dev/null
}
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
fail=0
case " $(bm -V '${TOOL_DEPENDS}') " in
*:../../devel/py-cppy" "*) ;;
*) echo "FAIL: no tool dependency on devel/py-cppy"; fail=1 ;;
esac
case " $(bm -V '${BUILDLINK_TREE}') " in
*" py-cppy "*) ;;
*) echo "FAIL: the target py-cppy is not buildlinked"; fail=1 ;;
esac
inc=$(bm -V '${BUILDLINK_DIR}/${PYSITELIB}/cppy/include')
case " $(bm -V '${CPPFLAGS}') " in
*" -I$inc "*) ;;
*) echo "FAIL: CPPFLAGS has no -I$inc"; fail=1 ;;
esac
[ "$fail" = 0 ] || exit 1
echo "PASS: cross py-kiwisolver takes the cppy headers from the buildlink tree"
