#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
set -eu
component=${1:?Specify layer-shell-qt, libkscreen, or kscreenlocker}
case "$component" in layer-shell-qt|libkscreen|kscreenlocker) ;; *) exit 2 ;; esac
: "${WORKSPACE_ROOT:=$HOME/.cache/emberbsd-plasma-workspace}"
: "${PLASMA_PREFIX:=$HOME/.cache/emberbsd-plasma-current/install}"
: "${JOBS:=1}"
recipe_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/pkg/sbin:/usr/X11R7/bin:/usr/bin:/bin:/usr/sbin:/sbin
: "${CC:=/usr/bin/cc}"
: "${CXX:=/usr/bin/c++}"
export CC CXX
export PKG_CONFIG_PATH="$PLASMA_PREFIX/lib/pkgconfig:/usr/pkg/lib/pkgconfig:/usr/X11R7/lib/pkgconfig"
mkdir -p "$WORKSPACE_ROOT/logs" "$PLASMA_PREFIX"
build_dir="$WORKSPACE_ROOT/build-$component"
/usr/pkg/qt6/bin/qt-cmake -S "$WORKSPACE_ROOT/src/$component-6.8.3" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$PLASMA_PREFIX" \
    -DCMAKE_PREFIX_PATH="$PLASMA_PREFIX;/usr/pkg/qt6;/usr/pkg;/usr/X11R7" \
    -DCMAKE_PROJECT_INCLUDE="$recipe_dir/prefer-current-prefix.cmake" \
    -DEMBERBSD_PLASMA_PREFIX="$PLASMA_PREFIX" \
    -DCMAKE_INSTALL_RPATH="$PLASMA_PREFIX/lib;/usr/pkg/lib;/usr/pkg/qt6/lib;/usr/X11R7/lib" \
    -DKDE_INSTALL_USE_QT_SYS_PATHS=OFF -DKDE_INSTALL_SYSCONFDIR=etc \
    -DKDE_INSTALL_QMLDIR=lib/qt6/qml -DKDE_INSTALL_QTPLUGINDIR=lib/qt6/plugins \
    -DKDE_INSTALL_LIBDIR=lib -DBUILD_TESTING=OFF -DBUILD_QCH=OFF \
    > "$WORKSPACE_ROOT/logs/$component-configure.log" 2>&1
cmake --build "$build_dir" --parallel "$JOBS" > "$WORKSPACE_ROOT/logs/$component-build.log" 2>&1
cmake --install "$build_dir" > "$WORKSPACE_ROOT/logs/$component-install.log" 2>&1
