#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted).
# A native consumer of the host-tools qt6-qttools must not buildlink
# QtDeclarative: that build has only the Linguist tools and
# qtattributionsscanner, and the native QtDeclarative needs the Qt GUI stack.
# archivers/kf6-karchive reaches qt6-qttools through linguist.mk.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
: "${BMAKE:?Set BMAKE to the Ports bmake}"
tree() {
	env MAKECONF="$makeconf" "$BMAKE" -C "$pkgsrc/archivers/kf6-karchive" \
	    MAKECONF="$makeconf" USE_CROSS_COMPILE=no \
	    PKG_BUILD_OPTIONS.qt6-qtbase=host-tools "$@" -V '${BUILDLINK_TREE}'
}
host=$(tree PKG_BUILD_OPTIONS.qt6-qttools=host-tools)
full=$(tree PKG_BUILD_OPTIONS.qt6-qttools=)
fail=0
case " $host " in
*" qt6-qttools "*) ;;
*) echo "FAIL: native kf6-karchive does not buildlink qt6-qttools"; fail=1 ;;
esac
case " $host " in
*" qt6-qtdeclarative "*) echo "FAIL: host-tools qt6-qttools buildlinks qt6-qtdeclarative"; fail=1 ;;
esac
case " $full " in
*" qt6-qtdeclarative "*) ;;
*) echo "FAIL: full qt6-qttools does not buildlink qt6-qtdeclarative"; fail=1 ;;
esac
[ "$fail" = 0 ] || exit 1
echo "PASS: only the full qt6-qttools buildlinks qt6-qtdeclarative"
