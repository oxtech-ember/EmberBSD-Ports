#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# Experimental native Plasma Workspace nested-session build.
set -eu
: "${WORKSPACE_ROOT:=$HOME/.cache/emberbsd-plasma-workspace}"
: "${JOBS:=1}"
recipe_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${PLASMA_PREFIX:=$HOME/.cache/emberbsd-plasma-current/install}"
: "${KWIN_VIRTUALKEYBOARD_XML:?Set to matching KWin org.kde.kwin.VirtualKeyboard.xml}"
export PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/pkg/sbin:/usr/X11R7/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PKG_CONFIG_PATH=/usr/pkg/lib/pkgconfig:/usr/X11R7/lib/pkgconfig
: "${CC:=/usr/bin/cc}"
: "${CXX:=/usr/bin/c++}"
export CC CXX
source_dir="$WORKSPACE_ROOT/src/plasma-workspace-6.8.3"
build_dir="$WORKSPACE_ROOT/build"
prefix="$WORKSPACE_ROOT/prefix"
mkdir -p "$WORKSPACE_ROOT/logs"
/usr/pkg/qt6/bin/qt-cmake -S "$source_dir" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DCMAKE_PREFIX_PATH="$PLASMA_PREFIX;/usr/pkg/qt6;/usr/pkg;/usr/X11R7" \
    -DCMAKE_PROJECT_INCLUDE="$recipe_dir/prefer-current-prefix.cmake" \
    -DEMBERBSD_PLASMA_PREFIX="$PLASMA_PREFIX" \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;$PLASMA_PREFIX/lib;/usr/pkg/lib;/usr/pkg/qt6/lib;/usr/X11R7/lib" \
    -DKDE_INSTALL_USE_QT_SYS_PATHS=OFF \
    -DKDE_INSTALL_SYSCONFDIR=etc \
    -DKDE_INSTALL_QMLDIR=lib/qt6/qml \
    -DKDE_INSTALL_QTPLUGINDIR=lib/qt6/plugins \
    -DKDE_INSTALL_LIBDIR=lib \
    -DBUILD_NESTED_SHELL_ONLY=ON -DWITH_X11=OFF -DWITH_X11_SESSION=OFF -DBUILD_TESTING=OFF \
    -DKWIN_VIRTUALKEYBOARD_INTERFACE="$KWIN_VIRTUALKEYBOARD_XML" \
    > "$WORKSPACE_ROOT/logs/configure.log" 2>&1
cmake --build "$build_dir" --parallel "$JOBS" > "$WORKSPACE_ROOT/logs/build.log" 2>&1
cmake --install "$build_dir" > "$WORKSPACE_ROOT/logs/install.log" 2>&1
