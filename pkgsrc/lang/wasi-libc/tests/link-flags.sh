#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake link-flags.sh PKGSRC MAKECONF
#
# CMake took the package LDFLAGS from the environment for the wasm links,
# so wasm-ld rejected -R/usr/pkg/lib when libc.so was linked. Configure the
# recipe (fetch and the host tools must be available) and check the linker
# flags that CMake recorded for the wasm links.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/lang/wasi-libc makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
ldflags=$(bm -V '${LDFLAGS}')
build=$(bm -V '${WRKDIR}/wasi-build')
bm clean >/dev/null 2>&1 || :
bm configure >/dev/null 2>&1 || { echo "FAIL: configure"; exit 1; }
status=0
for kind in EXE SHARED MODULE; do
	value=$(sed -n "s/^CMAKE_${kind}_LINKER_FLAGS:STRING=//p" "$build/CMakeCache.txt")
	[ -z "$value" ] || { echo "FAIL: CMAKE_${kind}_LINKER_FLAGS=$value"; status=1; }
done
bm clean >/dev/null 2>&1 || :
[ "$status" -eq 0 ] || exit 1
echo "PASS: wasm links do not take the package LDFLAGS ($ldflags)"
