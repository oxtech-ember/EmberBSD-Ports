#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted rust-bin regression.
#
# Usage: BMAKE=bmake patchelf-tool.sh PKGSRC MAKECONF
#
# post-install runs patchelf on the build host, so it must name the native
# patchelf from TOOL_DEPENDS. In a cross build ${PREFIX}/bin/patchelf is a
# target path that does not exist on the build host. List the commands of
# fix-relative-rpath without running them and check every patchelf there.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
recipe=$pkgsrc/lang/rust-bin
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}' 2>/dev/null)" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
cmds=$(bm -n fix-relative-rpath 2>/dev/null) || { echo "$0: bmake -n failed" >&2; exit 2; }
tools=$(printf '%s\n' "$cmds" | tr ' ;' '\n\n' | grep '/patchelf$' | sort -u)
[ -n "$tools" ] || { echo "FAIL: fix-relative-rpath runs no patchelf"; exit 1; }
status=0
for tool in $tools; do
	[ -x "$tool" ] || { echo "FAIL: post-install runs $tool, which the build host does not have"; status=1; }
done
[ "$status" -eq 0 ] || exit 1
echo "PASS: rust-bin post-install runs the native $tools"
