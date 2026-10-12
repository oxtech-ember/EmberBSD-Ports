#!/bin/sh
# SPDX-License-Identifier: MIT
# A disposable native source probe, not a package or system installer.
set -eu
umask 022
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: build.sh ABS_NEW_WORK [ABS_ARCHIVE_CACHE]' >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) echo 'Use an absolute work path.' >&2; exit 2 ;; esac
case "$work" in *[!a-zA-Z0-9_./-]*) echo 'Use a simple work path.' >&2; exit 2 ;; esac
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work path already exists.' >&2; exit 2; }
if [ "$#" = 2 ]; then
    case "$2" in /*) ;; *) echo 'Use an absolute archive cache.' >&2; exit 2 ;; esac
    [ -d "$2" ] || { echo 'Archive cache is not a directory.' >&2; exit 2; }
fi
jobs=${JOBS:-1}
case "$jobs" in ''|0|*[!0-9]*) echo 'JOBS must be positive.' >&2; exit 2 ;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'JOBS must be positive.' >&2; exit 2; }
build_as=${BUILD_AS_KIB:-}
if [ "${BUILD_AS_KIB+x}" = x ]; then
    case "$build_as" in ''|0|*[!0-9]*) echo 'BUILD_AS_KIB must be positive.' >&2; exit 2 ;; esac
    [ "$build_as" -gt 0 ] 2>/dev/null || { echo 'BUILD_AS_KIB must be positive.' >&2; exit 2; }
fi
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
mkdir "$work"
mkdir "$work/src" "$work/archives" "$work/logs"
prefix=$work/install
hash()
{
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1";
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
# Check all archives before extracting any, including cached archives.
while read -r name expected url; do
    if [ "$#" = 2 ]; then
        cp "$2/$name" "$work/archives/$name"
    else
        curl -fLsS --connect-timeout 20 --max-time 900 "$url" -o "$work/archives/$name"
    fi
    actual=$(hash "$work/archives/$name")
    [ "$actual" = "$expected" ] || { echo "Checksum mismatch: $name; nothing extracted." >&2; exit 2; }
    printf '%s %s %s\n' "$name" "$actual" "$url" >> "$work/logs/sources.txt"
done < "$recipe/sources.tsv"
[ "$(uname -s)" = NetBSD ] || { echo 'Native EmberBSD/NetBSD required.' >&2; exit 2; }
# Optional user-selected soft limit; preserve the inherited hard limit.
if [ -n "$build_as" ]; then
    ulimit -S -v "$build_as" || { echo 'Could not set the requested address-space limit.' >&2; exit 2; }
    [ "$(ulimit -S -v)" = "$build_as" ] || {
        echo 'Requested address-space limit verification failed.' >&2; exit 2;
    }
fi
CC=${CC:-/usr/bin/cc}
CXX=${CXX:-/usr/bin/c++}
for tool in "$CC" "$CXX" cmake ninja tar patch; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done
export CC CXX
printf '%s\n' "$(command -v "$CXX")" > "$work/logs/cxx.txt"
require_prefix()
{
    label=$1
    value=$2
    case "$value" in /*) ;; *) echo "Use an absolute $label prefix." >&2; exit 2 ;; esac
    case "$value" in *[!a-zA-Z0-9_./-]*) echo "Use a simple $label prefix." >&2; exit 2 ;; esac
    [ -d "$value" ] || { echo "Missing $label prefix: $value" >&2; exit 2; }
    printf '%s\n' "$value" > "$work/logs/$label-prefix.txt"
}
: "${EIGEN_PREFIX:?Set the common Eigen 5.0.1 prefix}"
: "${OPENCV_PREFIX:?Set the common headless OpenCV 5.0.0 prefix}"
require_prefix eigen "$EIGEN_PREFIX"
require_prefix opencv "$OPENCV_PREFIX"
PKG_CONFIG_PATH=/usr/pkg/lib/pkgconfig:/usr/pkg/share/pkgconfig
export PKG_CONFIG_PATH
{
    uname -a
    printf 'BUILD_AS_KIB=%s\nJOBS=%s\n' "$(ulimit -v)" "$jobs"
    "$CC" --version
    "$CXX" --version
    cmake --version
    ninja --version
} > "$work/logs/tools.txt"
run()
{
    stage=$1
    shift
    printf '%s\n' "$stage"
    status=0
    "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then
        tail -60 "$work/logs/$stage.log" >&2
        echo "Failed: $stage ($status)" >&2
        exit "$status"
    fi
}
: "${CERES_PREFIX:?Set the common Ceres 2.2.0 prefix}"
require_prefix ceres "$CERES_PREFIX"
source_name=open_vins-93adc241390d13e99232652cf05cbe18a93c7bea
# ov_data is 376 MiB and is not required by the analytic consumer.
tar -xzf "$work/archives/openvins-2.7.tar.gz" -C "$work/src" \
    "$source_name/ov_core" "$source_name/ov_init" "$source_name/ov_msckf" \
    "$source_name/config" "$source_name/LICENSE" "$source_name/ReadMe.md"
source_tree=$work/src/$source_name
run patch-ceres patch -d "$source_tree" -p1 -i "$recipe/patches/ceres-manifold-upstream.patch"
run patch-dependencies patch -d "$source_tree" -p1 -i "$recipe/patches/shared-dependencies.patch"
# Insert <cassert> where sources use assert() without it (32 files).
run patch-assert sh -c "cd '$source_tree' && grep -rl 'assert(' ov_core/src ov_msckf/src |
    while read fname; do
        grep -q cassert \"\$fname\" ||
            sed -i '1,/^#include/s/^#include/#include <cassert>\\n#include/' \"\$fname\"
    done"
# OpenCV 5.0 moved findFundamentalMat/FM_RANSAC from calib3d to the
# geometry module; the track sources only include features.hpp.
run patch-opencv5 sh "$recipe/patches/opencv5-geometry.sh" "$source_tree"
run openvins-configure cmake -S "$source_tree/ov_msckf" -B "$work/openvins-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_PREFIX_PATH="$EIGEN_PREFIX;$OPENCV_PREFIX;$CERES_PREFIX;/usr/pkg" \
    -DEigen3_DIR="$EIGEN_PREFIX/share/eigen3/cmake" \
    -DOpenCV_DIR="$OPENCV_PREFIX/lib/cmake/opencv5" -DCeres_DIR="$CERES_PREFIX/lib/cmake/Ceres" \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;$OPENCV_PREFIX/lib;$CERES_PREFIX/lib;/usr/pkg/lib" \
    -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
    -DCMAKE_DISABLE_FIND_PACKAGE_catkin=ON -DCMAKE_DISABLE_FIND_PACKAGE_ament_cmake=ON \
    -DENABLE_ROS=OFF -DENABLE_ARUCO_TAGS=OFF
run openvins-build cmake --build "$work/openvins-build" --parallel "$jobs"
run openvins-install cmake --install "$work/openvins-build"
licenses=$prefix/share/openvins-probe/licenses
mkdir -p "$licenses"
cp "$recipe/sources.tsv" "$recipe/PROVENANCE.md" "$prefix/share/openvins-probe/"
cp "$source_tree/LICENSE" "$licenses/OpenVINS-GPL-3.0.txt"
cp "$source_tree/ov_core/src/plot/LICENSE" "$licenses/matplotlibcpp-MIT.txt"
echo "Installed in $prefix; run test.sh to verify the installed consumer."
