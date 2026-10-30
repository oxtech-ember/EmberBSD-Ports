#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross Linguist consumers use the native TOOL package.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 PREPARED_PKGSRC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 work=$2
: "${BMAKE:?Set the native bmake executable}"
: "${MAKECONF:?Set the configured cross-package MAKECONF}"
mkdir "$work"
for consumer in devel/kf6-kcoreaddons sysutils/kf6-kdbusaddons archivers/kf6-karchive; do
    recipe=$pkgsrc/$consumer
    logs=$work/${consumer##*/}
    mkdir "$logs"
    "$BMAKE" -C "$recipe" -V '${DEPENDS}' > "$logs/dependencies.txt"
    "$BMAKE" -C "$recipe" -V '${TOOL_DEPENDS}' > "$logs/tool-dependencies.txt"
    "$BMAKE" -C "$recipe" -V '${CMAKE_CONFIGURE_ARGS}' > "$logs/cmake-args.txt"
    ! grep -q 'qt6-qttools' "$logs/dependencies.txt"
    grep -q 'qt6-qttools>=6.12.0' "$logs/tool-dependencies.txt"
    grep -q 'Qt6LinguistTools_DIR:PATH=/.*/qt6/lib/cmake/Qt6LinguistTools' "$logs/cmake-args.txt"
    if [ "$consumer" = devel/kf6-kcoreaddons ]; then
        grep -q 'qt6-qtdeclarative>=6.12.0' "$logs/dependencies.txt"
    else
        grep -q 'qt6-qtbase>=6.12.0' "$logs/dependencies.txt"
    fi
done
echo 'PASS: Linguist comes from the native qt6-qttools TOOL_DEPENDS; target QML dependency preserved'
