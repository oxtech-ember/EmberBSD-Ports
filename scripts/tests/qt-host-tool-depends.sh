#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross Qt consumers take QT_HOST_PATH from the
# native qt6-qtbase TOOL_DEPENDS package, never from an EMBERBSD_*HOST* path.
# Usage: qt-host-tool-depends.sh [BMAKE]
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
bmake=${1:-bmake}
tree=$root/pkgsrc
work=$(mktemp -d "${TMPDIR:-/tmp}/qt-host-tool-depends.XXXXXX")
trap 'rm -rf "$work"' EXIT
printf '.include "%s"\n' "$tree/x11/qt6-qtbase/host-tools.mk" > "$work/case.mk"
q() { "$bmake" -f "$work/case.mk" TOOLBASE=/tool EMBERBSD_QT_HOST_PATH=/wrong -V "\${$1}"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
[ "$(q QT_HOST_PATH)" = /tool/qt6 ] || fail "QT_HOST_PATH is not TOOLBASE/qt6"
case " $(q TOOL_DEPENDS) " in
*' qt6-qtbase>=6.12.0nb13:../../x11/qt6-qtbase '*) ;;
*) fail 'no native qt6-qtbase TOOL_DEPENDS' ;;
esac
args=$(q CMAKE_CONFIGURE_ARGS)
case " $args " in *' -DQT_HOST_PATH:PATH=/tool/qt6 '*) ;; *) fail 'CMake does not get QT_HOST_PATH' ;; esac
case "$args" in *wrong*) fail 'EMBERBSD_QT_HOST_PATH still selects host Qt' ;; esac
[ -z "$(q PKG_FAIL_REASON)" ] || fail 'fragment needs host path settings'
grep -q '^\.include "\.\./\.\./x11/qt6-qtbase/host-tools\.mk"$' "$tree/x11/qt6-qtbase/buildlink3.mk" ||
    fail 'qt6-qtbase/buildlink3.mk does not select native Qt for cross consumers'
# Linguist and Tools CMake packages come from the native qt6-qttools package.
printf '.include "%s"\n' "$tree/devel/qt6-qttools/host-tools.mk" > "$work/case.mk"
l() { "$bmake" -f "$work/case.mk" TOOLBASE=/tool EMBERBSD_QT_HOST_PATH=/wrong -V "\${$1}"; }
case " $(l TOOL_DEPENDS) " in
*' qt6-qttools>=6.12.0nb6:../../devel/qt6-qttools '*) ;;
*) fail 'no native qt6-qttools TOOL_DEPENDS for Linguist consumers' ;;
esac
args=$(l CMAKE_CONFIGURE_ARGS)
case " $args " in *' -DQt6LinguistTools_DIR:PATH=/tool/qt6/lib/cmake/Qt6LinguistTools '*) ;;
*) fail 'Linguist consumers do not use the TOOLBASE package' ;; esac
case "$args" in *wrong*) fail 'EMBERBSD_QT_HOST_PATH still selects Linguist' ;; esac
[ -z "$(l PKG_FAIL_REASON)" ] || fail 'Linguist fragment needs host path settings'
grep -q '^\.include "\.\./\.\./devel/qt6-qttools/host-tools\.mk"$' "$tree/devel/qt6-qttools/linguist.mk" ||
    fail 'cross Linguist consumers do not select the native qt6-qttools package'
if grep -rn 'EMBERBSD_QT_HOST' "$tree" --include='Makefile*' --include='*.mk' --include='*.conf'; then
    fail 'a recipe still reads an EMBERBSD_QT_HOST setting'
fi
if grep -rn 'QT_HOST_PATH[^ ]*=\${EMBERBSD_QT_HOST_PATH' "$tree" --include='Makefile*' --include='*.mk'; then
    fail 'a recipe passes EMBERBSD_QT_HOST_PATH as QT_HOST_PATH'
fi
echo 'PASS: cross Qt consumers use the native qt6-qtbase TOOL_DEPENDS prefix'
