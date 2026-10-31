#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Check that databases/postgresql18-client rewrites build-machine paths in
# the pgxs Makefile.global of a cross build. Without it check-wrkref
# stopped the package: "The above files still have references to the
# build directory".
#
# Usage: BMAKE=bmake postgresql18-client-cross-pgxs.sh PKGSRC MAKECONF
# MAKECONF is the mk.conf of a NetBSD cross build.

set -eu
[ $# -eq 2 ] || { echo "usage: BMAKE=bmake $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1
makeconf=$2
bmake=${BMAKE:-bmake}

v() {
	MAKECONF=$makeconf "$bmake" -C "$pkgsrc/databases/postgresql18-client" \
	    MAKECONF="$makeconf" -V "$1"
}
toolbase=$(v '${TOOLBASE}')
sysroot=$(v '${_CROSS_DESTDIR}')
localbase=$(v '${LOCALBASE}')
sed_args=$(v '${PGXS_CROSS_SED}')
if [ -z "$sed_args" ]; then
	echo "FAIL: the cross build installs pgxs with build-machine paths"
	exit 1
fi

out=$(eval "sed $sed_args" <<IN
BISON = $toolbase/bin/bison
install_bin = $toolbase/bin/bsdinstall -c
CPPFLAGS = -I$localbase/include -I$sysroot$localbase/include/libxml2
IN
)
expected="BISON = $localbase/bin/bison
install_bin = /usr/bin/install -c
CPPFLAGS = -I$localbase/include -I$localbase/include/libxml2"
if [ "$out" != "$expected" ]; then
	echo "FAIL: pgxs keeps build-machine paths:"
	echo "$out"
	exit 1
fi
echo "PASS: pgxs names the target's tools and include directories"
