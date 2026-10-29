#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Native consumer of the common package set.
set -eu
umask 022
[ "$#" = 3 ] || {
    echo 'Usage: build.sh COMMON_PREFIX ABS_NEW_WORK ABS_PORTS_DISTDIR' >&2; exit 2;
}
common=$1 work=$2 cache=$3
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work path already exists.' >&2; exit 2; }
[ -d "$cache" ] || { echo 'Fetch the archives with Ports fetch and pass its DISTDIR.' >&2; exit 2; }
jobs=${JOBS:-1}
case "$jobs" in ''|*[!0-9]*) jobs=0;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'JOBS must be positive.' >&2; exit 2; }
build_as=${BUILD_AS_KIB:-}
if [ "${BUILD_AS_KIB+x}" = x ]; then
    case "$build_as" in ''|*[!0-9]*) build_as=0;; esac
    [ "$build_as" -gt 0 ] 2>/dev/null || { echo 'BUILD_AS_KIB must be positive.' >&2; exit 2; }
fi
probe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
ports=$(CDPATH= cd "$probe/../.." && pwd -P)
recipe=$ports/pkgsrc/local-robotics/rtabmap
mkdir "$work"
mkdir "$work/source" "$work/archives" "$work/logs"
prefix=$work/install
hash() {
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1";
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
while read -r name expected url; do
    [ -n "$name" ] || continue
    [ -f "$cache/$name" ] || { echo "Missing $name; fetch it with Ports fetch." >&2; exit 2; }
    cp "$cache/$name" "$work/archives/$name"
    [ "$(hash "$work/archives/$name")" = "$expected" ] || {
        echo "Checksum mismatch: $name; nothing extracted." >&2; exit 2;
    }
    printf '%s %s %s\n' "$name" "$expected" "$url" >> "$work/logs/sources.txt"
done < "$probe/sources.tsv"
[ "$(uname -s):$(uname -p)" = NetBSD:aarch64 ] || { echo 'Native AArch64 EmberBSD required.' >&2; exit 2; }
[ -d "$common" ] || { echo 'Common dependency prefix is missing.' >&2; exit 2; }
common=$(CDPATH= cd "$common" && pwd -P)
CC=${CC:-$common/bin/clang}
CXX=${CXX:-$common/bin/clang++}
for compiler in "$CC" "$CXX"; do
    case "$compiler" in /*) ;; *) echo 'Use absolute compiler paths.' >&2; exit 2;; esac
    [ -x "$compiler" ] && [ "$("$compiler" -dumpversion)" = 23.1.4 ] || {
        echo 'The common Clang 23.1.4 compiler is required.' >&2; exit 2;
    }
    case "$("$compiler" -dumpmachine)" in aarch64*netbsd*) ;;
        *) echo 'Native AArch64 EmberBSD compiler required.' >&2; exit 2;; esac
done
for tool in cmake ninja tar patch; do command -v "$tool" >/dev/null || exit 2; done
for config in share/eigen3/cmake/Eigen3Config.cmake lib/cmake/opencv5/OpenCVConfig.cmake \
    share/pcl-1.15/PCLConfig.cmake lib/cmake/GTSAM/GTSAMConfig.cmake \
    lib/cmake/lz4/lz4Config.cmake; do
    [ -f "$common/$config" ] || { echo "Missing common dependency: $config" >&2; exit 2; }
done
for library in libpcl_surface.so libpcl_segmentation.so libpcl_ml.so libflann_cpp.so libsqlite3.so; do
    [ -f "$common/lib/$library" ] || { echo "Missing common library: $library" >&2; exit 2; }
done
if [ -n "$build_as" ]; then
    ulimit -S -v "$build_as"
    [ "$(ulimit -S -v)" = "$build_as" ] || exit 2
fi
unset COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
unset PKG_CONFIG_SYSROOT_DIR
PKG_CONFIG_PATH=
PKG_CONFIG_LIBDIR=$common/lib/pkgconfig:$common/share/pkgconfig
export CC CXX PKG_CONFIG_PATH PKG_CONFIG_LIBDIR
printf '%s\n' "$CC" > "$work/logs/cc.txt"
printf '%s\n' "$CXX" > "$work/logs/cxx.txt"
printf '%s\n' "$common" > "$work/logs/common-prefix.txt"
{
    uname -a
    printf 'BUILD_AS_KIB=%s\nJOBS=%s\n' "$(ulimit -v)" "$jobs"
    "$CC" --version
    "$CXX" --version
    cmake --version
    ninja --version
    printf 'features.cmake %s\n' "$(hash "$recipe/features.cmake")"
} > "$work/logs/tools.txt"
run() {
    stage=$1; shift
    status=0
    "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$work/logs/$stage.status"
    [ "$status" = 0 ] || { tail -60 "$work/logs/$stage.log" >&2; exit "$status"; }
}
run extract tar -xf "$work/archives/rtabmap-0.23.8.tar.gz" --strip-components=1 -C "$work/source"
for delta in "$recipe/patches/"patch-*; do
    [ -f "$delta" ] || continue
    printf '%s %s\n' "$(basename "$delta")" "$(hash "$delta")" >> "$work/logs/patch-inputs.txt"
    run "$(basename "$delta")" patch -f -N -F 0 -d "$work/source" -p1 < "$delta"
done
# The genuine native resource generator must load the new build-tree utilite.
# Installation replaces this build RPATH with the final installed paths.
run rtabmap-configure cmake -S "$work/source" -B "$work/rtabmap-build" -G Ninja \
    -C "$recipe/features.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_PREFIX_PATH="$common" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DEigen3_DIR="$common/share/eigen3/cmake" \
    -DOpenCV_DIR="$common/lib/cmake/opencv5" -DPCL_DIR="$common/share/pcl-1.15" \
    -DGTSAM_DIR="$common/lib/cmake/GTSAM" \
    -DSQLite3_INCLUDE_DIR="$common/include" -DSQLite3_LIBRARY="$common/lib/libsqlite3.so" \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=OFF \
    -DCMAKE_BUILD_RPATH="$common/lib;$common/llvm/lib" \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;$common/lib;$common/llvm/lib" \
    -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF
run rtabmap-build cmake --build "$work/rtabmap-build" --parallel "$jobs"
run rtabmap-install cmake --install "$work/rtabmap-build"
run rtabmap-licenses sh "$recipe/files/install-licenses.sh" "$work/source" "$prefix" "$recipe"
echo "Installed RTAB-Map in $prefix; run test.sh $work PATCHED_OPENCV_SOURCE."
