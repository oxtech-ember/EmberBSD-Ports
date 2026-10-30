#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-malloc-answers.sh PKGSRC MAKECONF
#
# Autoconf's AC_FUNC_MALLOC and AC_FUNC_REALLOC run a target program and
# answer "no" when cross compiling, so configure renames malloc and
# realloc to rpl_* replacements that most packages do not provide.
# libcddb then fails to compile. NetBSD returns a unique pointer for
# malloc(0) and realloc(NULL, 0), the answer a native configure finds.
# Configure libcddb with the cross profile and check its config.h.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/audio/libcddb makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
bm clean >/dev/null 2>&1 || :
bm configure >/dev/null 2>&1 || { echo "$0: bmake configure failed" >&2; exit 2; }
h=$(bm -V '${WRKSRC}')/config.h
status=0
for f in malloc realloc; do
	if grep -q "^#define $f rpl_$f" "$h"; then
		echo "FAIL: cross configure replaces $f with rpl_$f"; status=1
	fi
done
bm clean >/dev/null 2>&1 || :
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross configure uses the NetBSD malloc and realloc"
