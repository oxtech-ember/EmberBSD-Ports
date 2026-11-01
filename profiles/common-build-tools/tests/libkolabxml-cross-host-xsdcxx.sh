#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake libkolabxml-cross-host-xsdcxx.sh PKGSRC MAKECONF
#
# libkolabxml runs xsdcxx and its own xsdbin at build time. A cross build
# found no build-host xsdcxx (the target xsd is not runnable), and CMake
# stopped with "Could NOT find LibkolabxmlDependencies (missing: XSDCXX)";
# xsdbin was built for the target. The generated code and xsdbin use
# std::auto_ptr, which libc++ drops from C++17 on. Check that every build
# uses C++14, that a cross build depends on the native xsd and xerces-c,
# passes the host xsdcxx and xsdbin to CMake and stops early when xsdcxx is
# missing, and that a native build keeps the upstream lookups. MAKECONF
# selects a cross build.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/kolabxml-xsd.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
bm() {
	cross=$1; shift
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/textproc/libkolabxml" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/w" USE_CROSS_COMPILE=$cross \
	    _MAKEVARS_MK=defined "$@" </dev/null 2>/dev/null
}
fail() { echo "FAIL: $*" >&2; exit 1; }
[ "$(bm yes -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }

toolbase=$(bm yes -V '${TOOLBASE}')
bm yes -V '${TOOL_DEPENDS}' | tr ' ' '\n' | grep -q '^xsd>=4.0.0:../../devel/xsd$' ||
	fail "cross TOOL_DEPENDS has no native devel/xsd"
bm yes -V '${CMAKE_CONFIGURE_ARGS}' | tr ' ' '\n' |
    grep -qx -- "-DXSDCXX:FILEPATH=$toolbase/bin/xsdcxx" ||
	fail "cross CMake arguments do not name $toolbase/bin/xsdcxx"

bm yes -V '${TOOL_DEPENDS}' | tr ' ' '\n' |
    grep -q '^xerces-c>=3.1.1:../../textproc/xerces-c$' ||
	fail "cross TOOL_DEPENDS has no native textproc/xerces-c"
xsdbin=$(bm yes -V '${WRKDIR}')/.ember-host/xsdbin
bm yes -V '${CMAKE_CONFIGURE_ARGS}' | tr ' ' '\n' |
    grep -qx -- "-DXSDBIN:FILEPATH=$xsdbin" ||
	fail "cross CMake arguments do not name the host xsdbin"
for c in yes no; do
	[ "$(bm $c -V '${FORCE_CXX_STD}')" = c++14 ] ||
		fail "USE_CROSS_COMPILE=$c does not force C++14"
done

printf '#!/bin/sh\n' > "$tmp/xsdcxx"; chmod +x "$tmp/xsdcxx"
bm yes _EMBER_XSDCXX="$tmp/xsdcxx" emberbsd-host-xsdcxx-check >/dev/null ||
	fail "check rejects an executable xsdcxx"
if bm yes _EMBER_XSDCXX="$tmp/missing" emberbsd-host-xsdcxx-check >/dev/null; then
	fail "check accepts a missing xsdcxx"
fi

bm no -V '${TOOL_DEPENDS}' | tr ' ' '\n' | grep -q 'devel/xsd$' &&
	fail "native TOOL_DEPENDS has devel/xsd"
bm no -V '${CMAKE_CONFIGURE_ARGS}' | grep -q -- '-DXSD' &&
	fail "native CMake arguments set XSDCXX or XSDBIN"
echo PASS
