#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake apr-cross-installed-rules.sh PKGSRC MAKECONF
#
# apr installs build/apr_rules.out as libexec/apr/apr_rules.mk. configure
# records RM and CC_FOR_BUILD from the pkgsrc environment there, so a cross
# build installed build-host paths and stopped in the work-directory check.
# Run the post-build of devel/apr over rules files with build-host values
# and check that a cross build gives the installed copy RM=rm and
# CC_FOR_BUILD=$(CC), keeps the build copy, and that a native build changes
# neither. MAKECONF selects a cross build.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/apr-rules.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
bm() {
	cross=$1; shift
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/devel/apr" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/$cross" USE_CROSS_COMPILE=$cross \
	    "$@" </dev/null 2>/dev/null
}
rules='CC=cc
CC_FOR_BUILD=/build/host/bin/clang
RM=/build/host/bin/grm
AWK=awk'
# Write both rules files with build-host values, run post-build and print
# the build directory.
run() {
	b=$(bm "$1" -V '${WRKSRC}')/build
	mkdir -p "$b"
	printf '%s\n' "$rules" > "$b/apr_rules.mk"
	printf '%s\n' "$rules" > "$b/apr_rules.out"
	bm "$1" post-build >/dev/null || true
	echo "$b"
}
[ "$(bm yes -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
fail=0
b=$(run yes)
want='CC=cc
CC_FOR_BUILD=$(CC)
RM=rm
AWK=awk'
if [ "$(cat "$b/apr_rules.out")" != "$want" ]; then
	echo "FAIL: cross installed apr_rules.mk keeps build-host tools:"
	grep -E '^(RM|CC_FOR_BUILD)=' "$b/apr_rules.out" | sed 's/^/  /'
	fail=1
fi
if [ "$(cat "$b/apr_rules.mk")" != "$rules" ]; then
	echo "FAIL: cross build changed the apr_rules.mk that apr itself uses"
	fail=1
fi
b=$(run no)
if [ "$(cat "$b/apr_rules.out")" != "$rules" ]; then
	echo "FAIL: native build changed the installed apr_rules.mk"
	fail=1
fi
[ "$fail" = 0 ] || exit 1
echo "PASS: cross apr installs target RM and CC_FOR_BUILD; native unchanged"
