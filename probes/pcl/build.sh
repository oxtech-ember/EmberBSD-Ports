#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Native PCL consumer of the common dependency set.
set -eu
umask 022
[ "$#" -ge 2 ] && [ "$#" -le 3 ] || {
    echo 'Usage: build.sh COMMON_PREFIX ABS_NEW_WORK [ABS_ARCHIVE_CACHE]' >&2; exit 2;
}
common=$1 work=$2 cache=${3:-}
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work path already exists.' >&2; exit 2; }
[ -z "$cache" ] || [ -d "$cache" ] || { echo 'Archive cache is not a directory.' >&2; exit 2; }
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
recipe=$ports/pkgsrc/graphics/pcl
mkdir "$work"
mkdir "$work/source" "$work/archives" "$work/logs"
prefix=$work/install
hash() {
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1";
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
# Verify every selected source before extraction or the native OS check. The
# portable guard suite can exercise corrupt archives without target libraries.
while read -r name expected url; do
    [ -n "$name" ] || continue
    if [ -n "$cache" ]; then
        cp "$cache/$name" "$work/archives/$name"
    else
        curl -fLsS --connect-timeout 20 --max-time 900 "$url" -o "$work/archives/$name"
    fi
    actual=$(hash "$work/archives/$name")
    [ "$actual" = "$expected" ] || { echo "Checksum mismatch: $name; nothing extracted." >&2; exit 2; }
    printf '%s %s %s\n' "$name" "$actual" "$url" >> "$work/logs/sources.txt"
done < "$probe/sources.tsv"
[ "$(uname -s)" = NetBSD ] || { echo 'Native EmberBSD/NetBSD required.' >&2; exit 2; }
[ -d "$common" ] || { echo 'The common dependency prefix is missing.' >&2; exit 2; }
common=$(CDPATH= cd "$common" && pwd -P)
CC=${CC:-$common/gcc16/bin/gcc}
CXX=${CXX:-$common/gcc16/bin/g++}
for compiler in "$CC" "$CXX"; do
    case "$compiler" in /*) ;; *) echo 'Use absolute compiler paths.' >&2; exit 2;; esac
    [ -x "$compiler" ] && [ "$("$compiler" -dumpfullversion)" = 16.2.0 ] || {
        echo 'The common GCC 16.2.0 compiler is required.' >&2; exit 2;
    }
    case "$("$compiler" -dumpmachine)" in aarch64*netbsd*) ;;
        *) echo 'Native AArch64 EmberBSD compiler required.' >&2; exit 2;; esac
done
for tool in cmake ninja tar patch; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done
for item in 'share/eigen3/cmake/Eigen3ConfigVersion.cmake:5.0.1' \
    'lib/cmake/Boost-1.92.0/BoostConfigVersion.cmake:1.92.0' \
    'lib/cmake/flann/flann-config-version.cmake:1.9.2' \
    'lib/cmake/lz4/lz4ConfigVersion.cmake:1.10.0'; do
    file=${item%:*} version=${item##*:}
    [ -f "$common/$file" ] && grep -F "set(PACKAGE_VERSION \"$version\")" "$common/$file" >/dev/null || {
        echo "Common dependency version missing: $file ($version)" >&2; exit 2;
    }
done
for library in libflann_cpp.so liblz4.so libboost_iostreams.so libboost_random.so; do
    [ -f "$common/lib/$library" ] || { echo "Missing common library: $library" >&2; exit 2; }
done
# Optional user-selected soft limit; preserve the inherited hard limit.
if [ -n "$build_as" ]; then
    ulimit -S -v "$build_as" || { echo 'Could not set the requested address-space limit.' >&2; exit 2; }
    [ "$(ulimit -S -v)" = "$build_as" ] || { echo 'Address-space limit verification failed.' >&2; exit 2; }
fi
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
unset PKG_CONFIG_SYSROOT_DIR
export CC CXX
PKG_CONFIG_PATH=
PKG_CONFIG_LIBDIR=$common/lib/pkgconfig:$common/share/pkgconfig
export PKG_CONFIG_PATH PKG_CONFIG_LIBDIR
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
    stage=$1
    shift
    printf '%s\n' "$stage"
    status=0
    "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$work/logs/$stage.status"
    if [ "$status" -ne 0 ]; then
        tail -60 "$work/logs/$stage.log" >&2
        echo "Failed: $stage ($status)" >&2
        exit "$status"
    fi
}
run extract tar -xf "$work/archives/pcl-1.15.1.tar.gz" --strip-components=1 -C "$work/source"
for delta in "$recipe/patches/"patch-*; do
    [ -f "$delta" ] || continue
    printf '%s %s\n' "$(basename "$delta")" "$(hash "$delta")" >> "$work/logs/patch-inputs.txt"
    run "$(basename "$delta")" patch -f -N -F 0 -d "$work/source" -p1 < "$delta"
done
run pcl-configure cmake -S "$work/source" -B "$work/pcl-build" -G Ninja \
    -C "$recipe/features.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_PREFIX_PATH="$common" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;$common/lib;$common/gcc16/lib" \
    -DEigen3_DIR="$common/share/eigen3/cmake" \
    -DBoost_DIR="$common/lib/cmake/Boost-1.92.0" \
    -Dflann_DIR="$common/lib/cmake/flann" -Dlz4_DIR="$common/lib/cmake/lz4" \
    -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
    -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON
run pcl-build cmake --build "$work/pcl-build" --parallel "$jobs" --target \
    pcl_common pcl_kdtree pcl_octree pcl_search pcl_sample_consensus \
    pcl_filters pcl_features pcl_registration pcl_io pcl_io_ply pcl_surface pcl_segmentation pcl_ml
run pcl-install cmake --install "$work/pcl-build"
run pcl-licenses sh "$recipe/files/install-licenses.sh" "$work/source" "$prefix" "$recipe"
echo "Installed PCL in $prefix; run test.sh $work for the installed consumers."
