#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cython-tool-cross.sh PKGSRC MAKECONF
#
# devel/py-cython/tool.mk linked cython from PREFIX. In a cross build
# PREFIX is the target prefix, so libplist's configure found no cython and
# the package missed its Python bindings. Run the link target for
# textproc/libplist and require a cython that runs on the build machine,
# and a tool dependency on py-cython.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/textproc/libplist makeconf=$2
work=$(cd "$(mktemp -d "${TMPDIR:-/tmp}/cython-tool.XXXXXX")" && pwd -P)
trap 'rm -rf "$work"' EXIT
bm() {
	MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" \
	    WRKOBJDIR="$work/objects" BUILDLINK_DIR="$work/bl" "$@"
}
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
status=0
case " $(bm -V '${TOOL_DEPENDS}') " in
*" $(bm -V '${PYPKGPREFIX}')-cython-"*) ;;
*) echo "FAIL: no py-cython tool dependency"; status=1 ;;
esac
mkdir -p "$work/bl/bin"
bm buildlink-bin-cython >"$work/link.log" 2>&1 ||
	{ cat "$work/link.log"; echo "FAIL: buildlink-bin-cython"; exit 1; }
if ! "$work/bl/bin/cython" --version >/dev/null 2>&1; then
	echo "FAIL: no build machine cython in BUILDLINK_DIR/bin"; status=1
fi
[ "$status" -eq 0 ] && echo "PASS: cross cython tool runs on the build machine"
exit "$status"
