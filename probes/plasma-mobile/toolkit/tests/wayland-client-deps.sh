#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), test the real transitive consumer graph.
set -eu
[ "$#" = 2 ] || { echo 'Usage: wayland-client-deps.sh PKGSRC NEW_OUTPUT' >&2; exit 2; }
: "${BMAKE:?Set BMAKE}"
: "${MAKECONF:?Set the cross MAKECONF}"
mkdir "$2"
# Check a KCrash consumer and a KColorScheme consumer. The old buildlinks
# selected QtWayland 6.12, which no longer owns the Qt Wayland client module.
"$BMAKE" -C "$1/devel/kf6-kcrash" -v BUILDLINK_TREE > "$2/packages.txt"
"$BMAKE" -C "$1/devel/kf6-kcolorscheme" -v BUILDLINK_TREE >> "$2/packages.txt"
tr ' ' '\n' < "$2/packages.txt" > "$2/names.txt"
for package in qt6-qtbase kf6-kwindowsystem kf6-kguiaddons; do
    grep -Fxq "$package" "$2/names.txt"
done
if grep -Fxq qt6-qtwayland "$2/names.txt"; then
    echo 'Obsolete QtWayland client dependency reached KCrash' >&2; exit 1
fi
echo 'PASS: transitive Frameworks consumer uses the Qtbase Wayland client'
