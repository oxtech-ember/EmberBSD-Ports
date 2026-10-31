#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted).
# A cross build of a KDE application must take meinproc6 and the other
# documentation tools from the native kf6-kdoctools-generators package. The
# recipes name the full kf6-kdoctools as a tool, and its native build needs
# KI18n, QML and the Qt GUI stack, which the native host-tools Qt lacks.
# archivers/ark reaches kf6-kdoctools through buildlink3 files as well;
# games/bovo names it only as a tool.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$4
: "${BMAKE:?Set BMAKE to the Ports bmake}"
[ ! -e "$work" ] || { echo "Output exists: $work" >&2; exit 2; }
mkdir -p "$work"
fail=0
for pkg in archivers/ark games/bovo; do
	out=$work/$(echo "$pkg" | tr / _).txt
	env MAKECONF="$makeconf" "$BMAKE" -C "$pkgsrc/$pkg" MAKECONF="$makeconf" \
	    -V '${USE_CROSS_COMPILE:tl}' -V '${TOOL_DEPENDS}' \
	    -V '${CMAKE_CONFIGURE_ARGS:M-DMEINPROC6_EXECUTABLE=*}' > "$out"
	[ "$(sed -n 1p "$out")" = yes ] || { echo "SKIP setup: $pkg is not a cross build" >&2; exit 2; }
	tools=$(sed -n 2p "$out" | tr ' ' '\n')
	full=$(printf '%s\n' "$tools" | grep -c ':\.\./\.\./devel/kf6-kdoctools$' || true)
	gen=$(printf '%s\n' "$tools" | grep -c '^kf6-kdoctools-generators-6\.31\.0.*:\.\./\.\./devel/kf6-kdoctools-generators$' || true)
	meinproc=$(sed -n 3p "$out")
	if [ "$full" != 0 ]; then
		echo "FAIL: $pkg needs the full native kf6-kdoctools as a tool"; fail=1
	fi
	if [ "$gen" != 1 ]; then
		echo "FAIL: $pkg has $gen kf6-kdoctools-generators tool entries"; fail=1
	fi
	case $meinproc in
	*/bin/meinproc6) ;;
	*) echo "FAIL: $pkg does not pass the native meinproc6 to CMake"; fail=1;;
	esac
	[ "$fail" = 1 ] || echo "PASS: $pkg takes the documentation tools from kf6-kdoctools-generators"
done
exit $fail
