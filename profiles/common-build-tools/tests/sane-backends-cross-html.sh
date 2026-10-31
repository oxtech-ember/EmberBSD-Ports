#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Check that graphics/sane-backends lists the HTML pages made by sane-desc
# only in native builds. Configure leaves them out when cross-compiling,
# and the cross package stopped with "The following files are in the
# PLIST but not in" the destination directory.
#
# Usage: BMAKE=bmake sane-backends-cross-html.sh PKGSRC MAKECONF
# MAKECONF is the mk.conf of a cross build.

set -eu
[ $# -eq 2 ] || { echo "usage: BMAKE=bmake $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1
makeconf=$2
bmake=${BMAKE:-bmake}

v() {
	MAKECONF=$makeconf "$bmake" -C "$pkgsrc/graphics/sane-backends" \
	    MAKECONF="$makeconf" "$@"
}
fail=0
if ! grep -q '^${PLIST.html}share/doc/sane-backends/sane-backends.html$' \
    "$pkgsrc/graphics/sane-backends/PLIST"; then
	echo "FAIL: the PLIST lists the sane-desc HTML pages unconditionally"
	fail=1
fi
if [ -n "$(v -V '${PLIST.html}')" ]; then
	echo "FAIL: the cross build expects the sane-desc HTML pages"
	fail=1
fi
if [ "$(v USE_CROSS_COMPILE=no -V '${PLIST.html}')" != yes ]; then
	echo "FAIL: the native build does not list the HTML pages"
	fail=1
fi
[ $fail -eq 0 ] || exit 1
echo "PASS: only native builds list the sane-desc HTML pages"
