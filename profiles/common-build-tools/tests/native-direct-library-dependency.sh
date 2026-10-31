#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake native-direct-library-dependency.sh PKGSRC MAKECONF PKGPATH DEPPATH
#
# On macOS the strict Mach-O check (MACHO_USE_LOAD_COMMANDS) requires a
# direct full dependency for every pkgsrc library that a package's binaries
# load. A library that came in only through another package's buildlink
# file is not recorded, and check-shlibs rejects the native package: for
# x11/libXmu, libX11 is not a runtime dependency. Check that the native
# build of PKGPATH depends on DEPPATH directly.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF PKGPATH DEPPATH" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 pkgpath=$3 deppath=$4
depends=$(MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$pkgpath" MAKECONF="$makeconf" \
	USE_CROSS_COMPILE=no -V '${DEPENDS}' </dev/null)
for d in $depends; do
	case $d in *:../../"$deppath")
		echo "PASS: native $pkgpath depends on $deppath"; exit 0;;
	esac
done
echo "FAIL: native $pkgpath lacks a direct dependency on $deppath"
exit 1
