#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake configure.sh PKGSRC MAKECONF
#
# Configure the recipe for a target without the Blocks runtime and
# libdispatch, such as NetBSD. Only ld64 needs them, and the recipe builds
# codesign_allocate alone. libLTO must not come from the build machine's
# llvm-config either.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/devel/cctools makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
src=$(bm -V '${WRKSRC}')
trap 'bm clean >/dev/null 2>&1 || :' EXIT
bm clean >/dev/null 2>&1 || :
log=$(mktemp)
bm configure >"$log" 2>&1 || {
	echo "FAIL: configure: $(grep -i 'required library\|configure: error' "$log" | head -1)"
	rm -f "$log"; exit 1; }
rm -f "$log"
if grep -q 'checking for llvm-config' "$src/config.log"; then
	echo "FAIL: configure looked for llvm-config"; exit 1
fi
if grep -q '_Block_release\|dispatch_once' "$src/config.log"; then
	echo "FAIL: configure required the Blocks runtime or libdispatch"; exit 1
fi
echo "PASS: cctools configures without the Blocks runtime, libdispatch and libLTO"
