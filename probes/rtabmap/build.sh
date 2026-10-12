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
: "${PCL_PREFIX:?Set the common PCL 1.15.1 prefix, including io/surface/segmentation}"
: "${GTSAM_PREFIX:?Set the common GTSAM 4.3.0 prefix}"
: "${SQLITE_PREFIX:?Set the common SQLite 3.53.4 prefix}"
require_prefix pcl "$PCL_PREFIX"
require_prefix gtsam "$GTSAM_PREFIX"
require_prefix sqlite "$SQLITE_PREFIX"
tar -xzf "$work/archives/rtabmap-0.23.8.tar.gz" -C "$work/src"
source_tree=$work/src/rtabmap-d069becc724905d6465a8758c40dae88e13bb9e8
run patch-opencv5 patch -d "$source_tree" -p1 -i "$recipe/patches/opencv5-upstream.patch"
run patch-dependencies patch -d "$source_tree" -p1 -i "$recipe/patches/shared-headless-dependencies.patch"
run patch-gtsam4 sh "$recipe/patches/gtsam4-optional.sh" "$source_tree"
# Disable every optional backend in the pinned source; enable GTSAM explicitly.
# This avoids opportunistic linkage to packages installed by another probe.
set --
for option in $(sed -n 's/^[Oo][Pp][Tt][Ii][Oo][Nn](\(WITH_[A-Z0-9_]*\)[ 	].*/\1/p' "$source_tree/CMakeLists.txt" | sort -u); do
    [ "$option" = WITH_GTSAM ] || set -- "$@" "-D$option=OFF"
done
run rtabmap-configure cmake -S "$source_tree" -B "$work/rtabmap-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_PREFIX_PATH="$EIGEN_PREFIX;$OPENCV_PREFIX;$PCL_PREFIX;$GTSAM_PREFIX;$SQLITE_PREFIX;/usr/pkg" \
    -DEigen3_DIR="$EIGEN_PREFIX/share/eigen3/cmake" \
    -DOpenCV_DIR="$OPENCV_PREFIX/lib/cmake/opencv5" -DPCL_DIR="$PCL_PREFIX/share/pcl-1.15" \
    -DGTSAM_DIR="$GTSAM_PREFIX/lib/cmake/GTSAM" \
    -DSQLite3_INCLUDE_DIR="$SQLITE_PREFIX/include" -DSQLite3_LIBRARY="$SQLITE_PREFIX/lib/libsqlite3.so" \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;$OPENCV_PREFIX/lib;$PCL_PREFIX/lib;$GTSAM_PREFIX/lib;$SQLITE_PREFIX/lib;/usr/pkg/lib" \
    -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
    -DBUILD_SHARED_LIBS=ON -DBUILD_APP=OFF -DBUILD_TOOLS=OFF -DBUILD_EXAMPLES=OFF \
    -DWITH_GTSAM=ON -DPCL_OMP=OFF -DBUILD_OPENGV=OFF "$@"
run rtabmap-build cmake --build "$work/rtabmap-build" --parallel "$jobs"
run rtabmap-install cmake --install "$work/rtabmap-build"
licenses=$prefix/share/rtabmap-probe/licenses
mkdir -p "$licenses"
cp "$recipe/licenses/"*.txt "$licenses/"
cp "$recipe/sources.tsv" "$recipe/PROVENANCE.md" "$prefix/share/rtabmap-probe/"
cp "$source_tree/LICENSE" "$licenses/RTAB-Map-BSD.txt"
cp "$source_tree/utilite/include/rtabmap/utilite/UThread.h" "$licenses/utilite-LGPL-notice.h"
cp "$source_tree/corelib/src/rtflann/general.h" "$licenses/rtflann-BSD-notice.h"
cp "$source_tree/corelib/src/rtflann/ext/lz4.c" "$licenses/rtflann-lz4-BSD-notice.c"
echo "Installed in $prefix; run test.sh to verify the installed consumer."
