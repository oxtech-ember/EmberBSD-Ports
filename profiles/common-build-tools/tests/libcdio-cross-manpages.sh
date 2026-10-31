#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Check that a cross build of misc/libcdio keeps the shipped manual pages.
# With help2man found, src/Makefile runs "help2man ./cd-drive" and the
# other new programs; a cross build stopped with "help2man: can't get
# `--help' info from ./cd-drive". Native builds still regenerate them.
#
# Usage: BMAKE=bmake libcdio-cross-manpages.sh PKGSRC MAKECONF
# MAKECONF is the mk.conf of a NetBSD cross build.

set -eu
[ $# -eq 2 ] || { echo "usage: BMAKE=bmake $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1
makeconf=$2
bmake=${BMAKE:-bmake}

answer() {
	MAKECONF=$makeconf "$bmake" -C "$pkgsrc/misc/libcdio" \
	    MAKECONF="$makeconf" "$@" -V '${CONFIGURE_ENV:Mac_cv_path_HELP2MAN=*}'
}

true_tool=$(MAKECONF=$makeconf "$bmake" -C "$pkgsrc/misc/libcdio" \
    MAKECONF="$makeconf" -V '${TRUE}')
cross=$(answer)
if [ "$cross" != "ac_cv_path_HELP2MAN=$true_tool" ]; then
	echo "FAIL: the cross build would run help2man on target programs ('$cross')"
	exit 1
fi
native=$(answer USE_CROSS_COMPILE=no)
if [ -n "$native" ]; then
	echo "FAIL: the native build does not look for help2man ('$native')"
	exit 1
fi
echo "PASS: the cross build keeps the shipped manual pages; native builds use help2man"
