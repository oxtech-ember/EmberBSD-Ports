#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-python-build-module.sh PKGSRC MAKECONF PKGPATH DEPPATH
#
# A Python build backend runs on the build machine and imports its build
# modules with the build tool Python. A module that a recipe takes only from
# a buildlink file is installed for the target, and the backend cannot import
# it: math/py-kiwisolver stopped with "Missing setup required dependencies:
# cppy". Check that the cross build of PKGPATH has DEPPATH as a tool
# dependency.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF PKGPATH DEPPATH" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 pkgpath=$3 deppath=$4
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$pkgpath" MAKECONF="$makeconf" "$@" </dev/null; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
for d in $(bm -V '${TOOL_DEPENDS}'); do
	case $d in *:../../"$deppath")
		echo "PASS: cross $pkgpath imports $deppath from a tool dependency"; exit 0;;
	esac
done
echo "FAIL: cross $pkgpath has no tool dependency on $deppath"
exit 1
