#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
set -eu
: "${WORKSPACE_ROOT:=$HOME/.cache/emberbsd-plasma-workspace}"
recipe_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/bin:/bin
if [ -e "$WORKSPACE_ROOT/src" ] || [ -L "$WORKSPACE_ROOT/src" ]; then
    echo 'Refusing to reuse an existing source tree. Select a fresh WORKSPACE_ROOT or move its src directory aside.' >&2
    exit 1
fi
mkdir -p "$WORKSPACE_ROOT/archives"
mkdir "$WORKSPACE_ROOT/src"
while read -r component version url checksum; do
    case "$component" in ''|'#'*) continue ;; esac
    archive="$WORKSPACE_ROOT/archives/$component-$version.tar.xz"
    if [ ! -f "$archive" ]; then curl -fL "$url" -o "$archive"; fi
    actual=$(sha256 -q "$archive")
    [ "$actual" = "$checksum" ] || { echo "Checksum mismatch: $archive" >&2; exit 1; }
    tar -xf "$archive" -C "$WORKSPACE_ROOT/src"
done < "$recipe_dir/sources.tsv"
source_dir="$WORKSPACE_ROOT/src/plasma-workspace-6.8.3"
patch -d "$source_dir" -p1 < "$recipe_dir/0001-nested-shell-profile.patch"
patch -d "$WORKSPACE_ROOT/src" -p1 < "$recipe_dir/0002-netbsd-common-libraries.patch"
patch -d "$WORKSPACE_ROOT/src/libkscreen-6.8.3" -p1 < "$recipe_dir/0003-libkscreen-cxx23.patch"
patch -d "$WORKSPACE_ROOT/src/kscreenlocker-6.8.3" -p1 < "$recipe_dir/0004-kscreenlocker-cxx23.patch"
qdbuscpp2xml -A "$WORKSPACE_ROOT/src/kwin-6.8.3/src/virtualkeyboard_dbus.h" \
    -o "$WORKSPACE_ROOT/src/org.kde.kwin.VirtualKeyboard.xml"
printf '%s\n' "KWIN_VIRTUALKEYBOARD_XML=$WORKSPACE_ROOT/src/org.kde.kwin.VirtualKeyboard.xml"
