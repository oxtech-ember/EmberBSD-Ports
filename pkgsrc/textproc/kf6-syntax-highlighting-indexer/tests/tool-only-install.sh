#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted).
# The native KF6 generator packages install one tool. kf6.mk includes
# devel/cmake/build.mk, which adds cmake-install to do-install unless the
# package defined do-install first; then the whole framework is installed
# and the PLIST check fails. Dry-run do-install and require one command
# that installs only the tool.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 PKGSRC MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
: "${BMAKE:?Set BMAKE to the Ports bmake}"
[ ! -e "$work" ] || { echo "refusing existing work directory: $work" >&2; exit 2; }
mkdir -p "$work"
fail=0
for item in textproc/kf6-sonnet-parsetrigrams:parsetrigrams6 \
    textproc/kf6-syntax-highlighting-indexer:katehighlightingindexer; do
	pkg=${item%%:*} tool=${item#*:}
	out=$work/$(echo "$pkg" | tr / -).log
	env MAKECONF="$makeconf" "$BMAKE" -C "$pkgsrc/$pkg" \
	    MAKECONF="$makeconf" USE_CROSS_COMPILE=no WRKOBJDIR="$work/w" \
	    -n do-install > "$out" 2> "$out.err" ||
	    { echo "FAIL: $pkg: dry-run do-install failed"; fail=1; continue; }
	n=$(grep -c . "$out" || true)
	if [ "$n" != 1 ] || ! grep -q "/bin/$tool \\\\*\$\|/bin/$tool\$" "$out"; then
		echo "FAIL: $pkg: do-install runs more than the $tool install ($n commands)"
		fail=1
	fi
done
[ "$fail" = 0 ] || exit 1
echo "PASS: native KF6 generator packages install only their tool"
