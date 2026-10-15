#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Shared GCC16 CPU point-cloud package.
set -eu
umask 022
[ "$#" = 5 ] || { echo 'Usage: cross-build.sh GCC_PREFIX SYSROOT PCL_ARCHIVE GTEST_ARCHIVE NEW_OUTPUT' >&2; exit 2; }
compiler=$1 sysroot=$2 archive=$3 gtest_archive=$4 out=$5
for path do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple absolute paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
jobs=${CROSS_JOBS:-3}
case "$jobs" in ''|*[!0-9]*) exit 2;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || exit 2
ports=$(CDPATH= cd "$(dirname "$0")/../.." && pwd -P)
recipe=$ports/pkgsrc/local-robotics/pcl
for language in gcc g++; do
    [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpfullversion)" = 16.2.0 ]
    [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpmachine)" = aarch64--netbsd ]
done
expected=$(awk '$1=="pcl-1.15.1.tar.gz" {print $2}' "$ports/probes/pcl/sources.tsv")
[ "${#expected}" = 64 ]
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
expected=$(awk '$1=="googletest-1.18.0.tar.gz" {print $2}' "$ports/probes/pcl/test-sources.tsv")
[ "${#expected}" = 64 ]
printf '%s  %s\n' "$expected" "$gtest_archive" | sha256sum -c -
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
[ -f "$crt/crtbeginS.o" ] && [ -f "$runtime/libstdc++.so.7" ] && [ -f "$runtime/libatomic.so.3" ]
for config in share/eigen3/cmake/Eigen3Config.cmake lib/cmake/Boost-1.92.0/BoostConfig.cmake lib/cmake/flann/flann-config.cmake lib/cmake/lz4/lz4Config.cmake; do
    [ -f "$sysroot/usr/pkg/$config" ]
done
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
PKG_CONFIG_SYSROOT_DIR=$sysroot
PKG_CONFIG_LIBDIR=$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/lib/pkgconfig
PKG_CONFIG_PATH=
export PKG_CONFIG_SYSROOT_DIR PKG_CONFIG_LIBDIR PKG_CONFIG_PATH
mkdir -p "$out/source" "$out/gtest" "$out/logs"
sha256sum "$archive" "$gtest_archive" "$recipe/features.cmake" "$0" > "$out/inputs.sha256"
tar -xf "$archive" --strip-components=1 -C "$out/source"
tar -xf "$gtest_archive" --strip-components=1 -C "$out/gtest"
for delta in "$recipe/patches/"patch-*; do
    [ -f "$delta" ] || continue
    sha256sum "$delta" >> "$out/inputs.sha256"
    patch --batch --forward -F 0 -d "$out/source" -p1 < "$delta" >> "$out/logs/patches.log" 2>&1
done
cat > "$out/toolchain.cmake" <<CMAKE
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $compiler/bin/aarch64--netbsd-gcc)
set(CMAKE_CXX_COMPILER $compiler/bin/aarch64--netbsd-g++)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$runtime -march=armv8-a -Wl,-rpath,/usr/pkg/gcc16/lib")
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -march=armv8-a -Wl,-rpath,/usr/pkg/gcc16/lib -Wall -Wextra -Wabi=11 -isystem $headers -isystem $headers/aarch64--netbsd -isystem $headers/backward")
if(NOT CMAKE_FIND_ROOT_PATH)
  set(CMAKE_FIND_ROOT_PATH $sysroot)
endif()
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
CMAKE
cmake -S "$out/source" -B "$out/build" -G Ninja -C "$recipe/features.cmake" \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr/pkg -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_PREFIX_PATH=/usr/pkg \
    -DEigen3_DIR="$sysroot/usr/pkg/share/eigen3/cmake" \
    -DBoost_DIR="$sysroot/usr/pkg/lib/cmake/Boost-1.92.0" -Dflann_DIR="$sysroot/usr/pkg/lib/cmake/flann" \
    -DBUILD_global_tests=ON -DGTEST_SRC_DIR="$out/gtest/googletest" -DGTEST_INCLUDE_DIR="$out/gtest/googletest/include" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel "$jobs" --target \
    pcl_common pcl_kdtree pcl_octree pcl_search pcl_sample_consensus pcl_filters pcl_features pcl_registration pcl_io pcl_io_ply pcl_surface pcl_segmentation pcl_ml \
    test_common test_pointcloud test_transforms test_filters_grid_minimum test_morphological test_filters_functor test_uniform_sampling \
    test_warps test_correspondence_estimation test_registration test_kdtree_search test_flann_search test_concave_prism test_ear_clipping > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
sh "$recipe/files/install-licenses.sh" "$out/source" "$out/stage/usr/pkg" "$recipe"
cmake -S "$ports/probes/pcl/tests" -B "$out/consumer" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    "-DCMAKE_FIND_ROOT_PATH=$out/stage/usr/pkg;$sysroot" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DPROBE_PREFIX="$out/stage/usr/pkg" \
    -DFLANN_PREFIX="$sysroot/usr/pkg" -DBOOST_PREFIX="$sysroot/usr/pkg" -DEIGEN_PREFIX="$sysroot/usr/pkg" \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' > "$out/logs/consumer-configure.log" 2>&1
cmake --build "$out/consumer" --parallel 2 > "$out/logs/consumer-build.log" 2>&1
find "$out/stage/usr/pkg/lib" -type f -name '*.so*' -exec "$compiler/bin/aarch64--netbsd-readelf" -h -d {} + > "$out/elf.txt"
[ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 13 ]
"$compiler/bin/aarch64--netbsd-readelf" -h -d "$out/consumer/pcl-contract" "$out/consumer/pcl-matrix-check" "$out/consumer/lz4-zero-buffers" "$out/consumer/boost-iostreams-contract" "$out/consumer/pcl-expanded-contract" >> "$out/elf.txt"
[ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 18 ]
for name in test_common test_pointcloud test_transforms test_filters_grid_minimum test_morphological test_filters_functor test_uniform_sampling test_warps test_correspondence_estimation test_registration test_kdtree_search test_flann_search test_concave_prism test_ear_clipping; do
    binary=$(find "$out/build/test" -type f -name "$name")
    [ -n "$binary" ] && [ -f "$binary" ]
    "$compiler/bin/aarch64--netbsd-readelf" -h -d "$binary" >> "$out/elf.txt"
done
[ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 32 ]
for path in "$compiler" "$sysroot" "$out"; do
    if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$path"; then echo 'Build-host runtime path leaked.' >&2; exit 1; fi
done
(cd "$out/stage/usr/pkg" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/files.txt"
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$out/expected-files.txt"
cmp "$out/files.txt" "$out/expected-files.txt"
echo "Staged PCL: $out/stage/usr/pkg"
