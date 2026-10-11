#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Host build only; run the consumer on EmberBSD.
set -eu
[ "$#" = 5 ] || { echo "Usage: $0 CROSS_TOOLS SYSROOT HOST_QT KF6_HOST_TOOLING NEW_WORK" >&2; exit 2; }
tools=$1 sysroot=$2 host_qt=$3 host_kf=$4 work=$5
: "${CMAKE:?Set the native CMake executable}"
: "${NINJA:?Set the native Ninja executable}"
: "${PKG_CONFIG:?Set the native pkg-config executable}"
for path in "$tools" "$sysroot" "$host_qt" "$host_kf" "$work" "$CMAKE" "$NINJA" "$PKG_CONFIG"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
done
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$work"
export PKG_CONFIG_SYSROOT_DIR="$sysroot"
export PKG_CONFIG_LIBDIR="$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/pkg/share/pkgconfig"
PKG_CONFIG_PATH=; export PKG_CONFIG_PATH
PATH="$(dirname "$CMAKE"):$PATH"; export PATH
sh "$sysroot/usr/pkg/qt6/bin/qt-cmake" -S "$src" -B "$work" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" \
    -DCMAKE_SYSTEM_NAME=NetBSD -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
    -DCMAKE_SYSROOT="$sysroot" -DCMAKE_FIND_ROOT_PATH="$sysroot" \
    -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
    -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY \
    -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
    -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY \
    -DCMAKE_CXX_COMPILER="$tools/bin/aarch64--netbsd-g++" \
    -DCMAKE_CXX_FLAGS="-B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
    -DCMAKE_EXE_LINKER_FLAGS="-L$sysroot/usr/pkg/gcc16/lib -L$sysroot/usr/pkg/lib" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_INSTALL_RPATH='/usr/pkg/qt6/lib;/usr/pkg/gcc16/lib;/usr/pkg/lib' \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    -DPKG_CONFIG_EXECUTABLE="$PKG_CONFIG" -DQT_HOST_PATH="$host_qt" -DKF6_HOST_TOOLING="$host_kf"
"$CMAKE" --build "$work" --parallel 2
file "$work/kconfig-consumer"
shasum -a 256 "$src"/* "$work/kconfig-consumer" > "$work/inputs-output.sha256"
