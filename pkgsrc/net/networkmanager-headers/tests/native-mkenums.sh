#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake native-mkenums.sh PKGSRC MAKECONF
#
# The enum-types headers are generated on the build host by glib-mkenums,
# a Python script. It must come from the native glib2-tools package in
# TOOLBASE, with its native Python, not from whatever the build host has
# installed elsewhere.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$1" MAKECONF="$makeconf" "$2" "$3"; }
recipe=net/networkmanager-headers
toolbase=$(bm $recipe -V '${TOOLBASE}')
deps=$(bm $recipe -V '${TOOL_DEPENDS}')
tool=$(bm $recipe -n do-install 2>/dev/null | awk '/glib-mkenums/ { print $1; exit }')
status=0
case $tool in
"$toolbase"/bin/glib-mkenums) ;;
*) echo "FAIL: enum headers use $tool, not $toolbase/bin/glib-mkenums"; status=1 ;;
esac
case " $deps " in
*:../../devel/glib2-tools" "*) ;;
*) echo "FAIL: TOOL_DEPENDS does not provide glib2-tools"; status=1 ;;
esac
grep -qx 'bin/glib-mkenums' "$pkgsrc/devel/glib2-tools/PLIST" ||
	{ echo "FAIL: glib2-tools does not install bin/glib-mkenums"; status=1; }
[ "$status" -eq 0 ] || exit 1
echo "PASS: networkmanager-headers runs the native glib-mkenums"
