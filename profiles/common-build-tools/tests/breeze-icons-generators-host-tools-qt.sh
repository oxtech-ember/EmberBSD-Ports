#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake breeze-icons-generators-host-tools-qt.sh PKGSRC MAKECONF HOST_PREFIX NEW_WORK
#
# The native qt6-qtbase of a cross build has the host-tools option: no Qt Gui.
# The Breeze Icons generators need only Qt Core, but the top-level
# CMakeLists.txt required Qt Gui, so breeze-icons-generators stopped at
# configure. Patch and configure the generators with the recipe's arguments
# against HOST_PREFIX, whose Qt must have no Qt6Gui package.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF HOST_PREFIX NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 host=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
[ -d "$host/qt6/lib/cmake/Qt6Core" ] && [ ! -e "$host/qt6/lib/cmake/Qt6Gui" ] ||
	{ echo "$0: $host has no Qt without Qt Gui" >&2; exit 2; }
mkdir "$4"
work=$4
bm() {
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" \
	    -C "$pkgsrc/graphics/breeze-icons-generators" \
	    MAKECONF="$makeconf" USE_CROSS_COMPILE=no _PKGSRC_BARRIER=yes \
	    "$@" </dev/null 2>/dev/null
}
tar -xJf "$(bm -V '${DISTDIR}/${DISTFILES}')" -C "$work"
src=$(echo "$work"/breeze-icons-*)
for p in $(bm -V '${PATCHDIR}')/patch-*; do
	"$host/bin/gpatch" -s -d "$src" -p0 < "$p"
done
args=$(bm -V '${CMAKE_CONFIGURE_ARGS:M-D*:N-DCMAKE_*}')
mkdir "$work/build"
# shellcheck disable=SC2086 # args are the recipe -D words.
if ! (cd "$work/build" && "$host/bin/cmake" $args \
    -DCMAKE_C_COMPILER="$host/bin/clang" -DCMAKE_CXX_COMPILER="$host/bin/clang++" \
    -DCMAKE_PREFIX_PATH="$host/qt6;$host" \
    "$src" > "$work/configure.log" 2>&1); then
	echo "FAIL: generators configure: $(grep -m1 -E 'Failed to find required|Could not find|CMake Error' "$work/configure.log" | tr -s ' ')"
	exit 1
fi
echo "PASS: Breeze Icons generators configure with the host-tools Qt ($args)"
