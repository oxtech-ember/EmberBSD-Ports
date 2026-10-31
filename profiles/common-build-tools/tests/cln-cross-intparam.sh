#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cln-cross-intparam.sh PKGSRC MAKECONF
#
# cln's configure derives integer sizes from compile-only probes. The
# signed probes overflowed, which made the bound non-constant; clang++
# accepted it as a variable length array, so int_bitsize came out as 31
# and intparam.h stopped the build. Configure cln with the cross profile
# and check the generated sizes and that aclocal would not rerun.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/math/cln makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
bm clean >/dev/null 2>&1 || :
bm configure >/dev/null 2>&1 || { echo "$0: bmake configure failed" >&2; exit 2; }
w=$(bm -V '${WRKSRC}')
h=$w/include/cln/intparam.h
status=0
if grep -q '^#error' "$h"; then
	echo "FAIL: intparam.h has an #error:"; grep '^#error' "$h"; status=1
fi
for v in char_bitsize:8 short_bitsize:16 int_bitsize:32 long_bitsize:64 \
    long_long_bitsize:64; do
	grep -q "^#define ${v%%:*} ${v#*:}\$" "$h" ||
		{ echo "FAIL: intparam.h lacks ${v%%:*} ${v#*:}"; status=1; }
done
if [ "$w/m4/intparam.m4" -nt "$w/aclocal.m4" ]; then
	echo "FAIL: m4/intparam.m4 is newer than aclocal.m4"; status=1
fi
bm clean >/dev/null 2>&1 || :
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross configure finds the aarch64 integer sizes"
