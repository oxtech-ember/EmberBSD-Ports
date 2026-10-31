#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake python-darwin-abi3-plist.sh PKGSRC MAKECONF
#
# Python 3.15 on Darwin names stable-ABI modules *.abi3-darwin.so, and the
# native Darwin build of archivers/py-brotlicffi installed a module its PLIST
# did not list. Check that the native PLIST of py-brotlicffi names the
# stable-ABI suffix of the build Python, and that a cross build for another
# platform keeps the portable *.abi3.so name. MAKECONF selects a cross build.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/abi3-plist.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
bm() {
	cross=$1; shift
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/archivers/py-brotlicffi" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/$cross" USE_CROSS_COMPILE=$cross "$@" </dev/null 2>/dev/null
}
module() {
	bm "$1" plist >/dev/null
	sed -n 's,^.*/brotlicffi/\(_brotlicffi\..*\)$,\1,p' "$(bm "$1" -V '${PLIST}')"
}
[ "$(bm yes -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
python=$(bm no -V '${PYTHONBIN}')
suffix=$("$python" -c 'import importlib.machinery as m
print([s for s in m.EXTENSION_SUFFIXES if s.startswith(".abi3")][0])')
fail=0
native=$(module no)
[ "$native" = "_brotlicffi$suffix" ] ||
	{ echo "FAIL: native PLIST lists $native, $python builds _brotlicffi$suffix"; fail=1; }
target=$(module yes)
[ "$target" = _brotlicffi.abi3.so ] ||
	{ echo "FAIL: cross PLIST lists $target, not _brotlicffi.abi3.so"; fail=1; }
[ "$fail" = 0 ] || exit 1
echo "PASS: py-brotlicffi PLIST names the stable-ABI suffix of its platform"
