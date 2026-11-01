#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake gts-cross-predicates.sh PKGSRC CROSS_MAKECONF NEW_WORK
#
# gts runs its predicates_init generator during the build to write
# predicates_init.h. A cross build compiled the generator for the target,
# so the build host could not run it. Build graphics/gts with the cross
# configuration and check that the generator runs on the build host and
# that its output is the header the library was built with.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 PKGSRC CROSS_MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
mkdir "$work"
fail() { echo "FAIL: $*" >&2; exit 1; }
bm() {
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/graphics/gts" \
	    MAKECONF="$makeconf" WRKOBJDIR="$work/w" USE_CROSS_COMPILE=yes \
	    "$@" </dev/null
}
src=$(bm -V '${WRKSRC}')/src
bm build > "$work/build.log" 2>&1 ||
	{ tail -20 "$work/build.log" >&2; fail "graphics/gts cross build failed"; }
[ -x "$src/predicates_init" ] || fail "predicates_init was not built"
"$src/predicates_init" > "$work/predicates_init.h" ||
	fail "predicates_init does not run on the build host"
grep -q '^static double splitter = ' "$work/predicates_init.h" ||
	fail "predicates_init printed no error bounds"
cmp -s "$work/predicates_init.h" "$src/predicates_init.h" ||
	fail "predicates_init.h differs from the host generator output"
echo PASS
