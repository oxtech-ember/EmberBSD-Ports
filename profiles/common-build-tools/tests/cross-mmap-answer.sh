#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-mmap-answer.sh PKGSRC MAKECONF
#
# Autoconf's AC_FUNC_MMAP runs a target program and answers "no" when
# cross compiling, so configure leaves HAVE_MMAP undefined. sane-backends
# then fails: "mmap(2) not available". NetBSD has a working mmap, the
# answer a native configure finds. Configure expat, which uses
# AC_FUNC_MMAP, with the cross profile and check its expat_config.h.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/textproc/expat makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
bm clean >/dev/null 2>&1 || :
bm configure >/dev/null 2>&1 || { echo "$0: bmake configure failed" >&2; exit 2; }
h=$(bm -V '${WRKSRC}')/expat_config.h
status=0
grep -q '^#define HAVE_MMAP 1' "$h" ||
	{ echo "FAIL: cross configure does not find the NetBSD mmap"; status=1; }
bm clean >/dev/null 2>&1 || :
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross configure uses the NetBSD mmap"
