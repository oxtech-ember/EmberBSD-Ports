#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake kf6-ki18n-host-tools-qml.sh PKGSRC MAKECONF HOST_PREFIX NEW_WORK
#
# The native qt6-qtbase of a cross build has the host-tools option: no Qt Gui
# and no Qt Qml. The native kf6-ki18n required Qt Qml through
# qt6-qtdeclarative, whose Qt Quick dependencies (qt6-qtshadertools,
# qt6-qtsvg, qt6-qtimageformats) skip their build without Qt Gui and stopped
# at install. Configure KI18n with the recipe's arguments for a host-tools
# qt6-qtbase against HOST_PREFIX, whose Qt must have no Qt6Qml package.
# KDECMakeSettings also enables the tests, which need Qt Test.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF HOST_PREFIX NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 host=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
[ -d "$host/qt6/lib/cmake/Qt6Core" ] && [ ! -e "$host/qt6/lib/cmake/Qt6Qml" ] ||
	{ echo "$0: $host has no Qt without Qt Qml" >&2; exit 2; }
mkdir "$4"
work=$4
bm() {
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/devel/kf6-ki18n" \
	    MAKECONF="$makeconf" USE_CROSS_COMPILE=no \
	    PKG_BUILD_OPTIONS.qt6-qtbase=host-tools _PKGSRC_BARRIER=yes \
	    "$@" </dev/null
}
fail=0
case " $(bm -V '${BUILDLINK_TREE}') " in
*" qt6-qtdeclarative "*)
	echo "FAIL: kf6-ki18n depends on qt6-qtdeclarative with a host-tools Qt"
	fail=1 ;;
esac
tar -xJf "$(bm -V '${DISTDIR}/${DISTFILES}')" -C "$work"
src=$(echo "$work"/ki18n-*)
args=$(bm -V '${CMAKE_CONFIGURE_ARGS:M-DBUILD_*}')
mkdir "$work/build"
# shellcheck disable=SC2086 # args are the recipe -DBUILD_* words.
(cd "$work/build" && "$host/bin/cmake" $args \
    -DCMAKE_C_COMPILER="$host/bin/clang" -DCMAKE_CXX_COMPILER="$host/bin/clang++" \
    -DCMAKE_PREFIX_PATH="$host/qt6;$host" \
    -DLibIntl_INCLUDE_DIRS="$host/include/gettext" \
    -DLibIntl_LIBRARIES="$host/lib/libintl.dylib" \
    -DPython3_EXECUTABLE="$(ls "$host"/bin/python3.[0-9]* | sed -n '/[0-9]$/p' | head -1)" \
    "$src" > "$work/configure.log" 2>&1) || {
	echo "FAIL: KI18n configure: $(grep -m1 -A2 'CMake Error' "$work/configure.log" | tr -s ' \n' ' ')"
	fail=1
}
[ "$fail" = 0 ] || exit 1
echo "PASS: KI18n configures with the host-tools Qt (${args:-no -DBUILD_* argument})"
