#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake test-stage1flex.sh RECIPE MAKECONF WRKOBJDIR
#
# A cross build compiles stage1flex with the build machine compiler but
# with the config.h of the target. NetBSD has <libintl.h>, so config.h
# enables NLS, and stage1flex stopped with "'libintl.h' file not found"
# on a build machine whose compiler does not find it. Build the recipe
# and check that stage1flex and flex were built and that flex keeps NLS.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 RECIPE MAKECONF WRKOBJDIR" >&2; exit 2; }
recipe=$1 makeconf=$2 obj=$3
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" \
    WRKOBJDIR="$obj" SKIP_DEPENDS=yes "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "FAIL: MAKECONF is not a cross build"; exit 1; }
src=$(bm -V '${WRKSRC}')
log=$(mktemp)
trap 'bm clean >/dev/null 2>&1 || :; rm -f "$log"' EXIT
bm clean >/dev/null 2>&1 || :
if ! bm build >"$log" 2>&1; then
	grep -m 3 -e 'error:' -e '\*\*\*' "$log" || tail -n 20 "$log"
	echo "FAIL: devel/flex does not build"; exit 1
fi
[ -x "$src/src/stage1flex" ] || { echo "FAIL: no stage1flex"; exit 1; }
[ -f "$src/src/flex" ] || { echo "FAIL: no flex"; exit 1; }
grep -q '^#define ENABLE_NLS 1' "$src/src/config.h" ||
	{ echo "FAIL: flex was configured without NLS"; exit 1; }
echo "PASS: stage1flex builds without NLS on the build machine; flex keeps NLS"
