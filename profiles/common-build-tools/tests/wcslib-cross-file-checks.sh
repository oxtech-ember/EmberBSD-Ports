#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake wcslib-cross-file-checks.sh PKGSRC MAKECONF
#
# wcslib's configure finds CFITSIO with AC_CHECK_FILE, which stops a cross
# build with "cannot check for file existence when cross compiling".
# Configure the recipe (its CFITSIO dependency must be installed) and
# check that configure finished and kept CFITSIO.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/graphics/wcslib makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
src=$(bm -V '${WRKSRC}')
trap 'bm clean >/dev/null 2>&1 || :' EXIT
bm clean >/dev/null 2>&1 || :
log=$(mktemp)
bm configure >"$log" 2>&1 || {
	echo "FAIL: configure: $(grep 'configure: error' "$log" | head -1)"
	rm -f "$log"; exit 1; }
rm -f "$log"
grep -q '^[[:space:]]*CFITSIOINC[[:space:]]*:*=[[:space:]]*-I' "$src/makedefs" ||
	{ echo "FAIL: configure did not keep CFITSIO"; exit 1; }
echo "PASS: wcslib configures with CFITSIO when cross compiling"
