#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake graphviz-cross-quartz.sh PKGSRC MAKECONF
#
# graphviz offered the macOS Quartz plugin whenever the build host had
# /System/Library/Frameworks/Quartz.framework, so a cross build for a
# NetBSD target on a Mac selected quartz (configure also tests the host
# framework directory) and left out x11. Check that a cross build disables
# quartz and keeps the x11 default, and that a native Darwin build still
# selects quartz.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/graphviz-quartz.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
bm() {
	cross=$1; shift
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/graphics/graphviz" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/w" USE_CROSS_COMPILE=$cross \
	    _MAKEVARS_MK=defined "$@" </dev/null 2>/dev/null
}
fail() { echo "FAIL: $*" >&2; exit 1; }
has() { tr ' ' '\n' | grep -qx -- "$1"; }
[ "$(bm yes -V '${OPSYS}')" != Darwin ] ||
	fail "the cross target is Darwin; this check needs a non-Darwin target"
bm yes -V '${PKG_OPTIONS}' | has quartz && fail "cross PKG_OPTIONS enable quartz"
bm yes -V '${CONFIGURE_ARGS}' | has --without-quartz ||
	fail "cross configure does not disable quartz"
bm yes -V '${PKG_OPTIONS}' | has x11 || fail "cross PKG_OPTIONS lose the x11 default"
if [ "$(bm no -V '${OPSYS}')" = Darwin ] &&
    [ -d /System/Library/Frameworks/Quartz.framework ]; then
	bm no -V '${PKG_OPTIONS}' | has quartz ||
		fail "native Darwin PKG_OPTIONS lose quartz"
fi
echo PASS
