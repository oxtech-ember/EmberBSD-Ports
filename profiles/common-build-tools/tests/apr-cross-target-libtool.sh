#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake apr-cross-target-libtool.sh PKGSRC MAKECONF
#
# apr installs a libtool for apr-1-config --apr-libtool. The cross build
# copied PKG_LIBTOOL, the libtool of the build host with a host shell
# interpreter, into the target package and stopped in check-interpreter.
# Run the post-install of devel/apr in a scratch work directory and check
# that a cross build links the target libtool of libtool-base and depends on
# it, and that a native build still installs a copy of PKG_LIBTOOL.
# MAKECONF selects a cross build.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/apr-libtool.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
bm() {
	cross=$1; shift
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/devel/apr" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/$cross" USE_CROSS_COMPILE=$cross \
	    "$@" </dev/null 2>/dev/null
}
# Run post-install over the libtool that make install left, and print its
# path.
installed() {
	lt=$(bm "$1" -V '${DESTDIR}${PREFIX}/libexec/apr/libtool')
	mkdir -p "${lt%/*}"
	: > "$lt"
	bm "$1" post-install >/dev/null
	echo "$lt"
}
[ "$(bm yes -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
fail=0
lt=$(installed yes)
want=$(bm yes -V '${PREFIX}/bin/libtool')
if [ ! -h "$lt" ] || [ "$(readlink "$lt")" != "$want" ]; then
	echo "FAIL: cross libexec/apr/libtool is not a link to $want"
	fail=1
fi
case " $(bm yes -V '${DEPENDS}') " in
*:../../devel/libtool-base" "*) ;;
*) echo "FAIL: cross apr does not depend on devel/libtool-base"; fail=1 ;;
esac
lt=$(installed no)
if [ -h "$lt" ] || ! cmp -s "$lt" "$(bm no -V '${PKG_LIBTOOL}')"; then
	echo "FAIL: native libexec/apr/libtool is not a copy of PKG_LIBTOOL"
	fail=1
fi
[ "$fail" = 0 ] || exit 1
echo "PASS: cross apr links the target libtool, native apr copies PKG_LIBTOOL"
