#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Shared Clang headless mapping core.
set -eu
umask 022
[ "$#" = 5 ] || { echo 'Usage: cross-build.sh CROSS_TOOLS SYSROOT ARCHIVE NATIVE_RES_TOOL NEW_OUTPUT' >&2; exit 2; }
tools=$1 sysroot=$2 archive=$3 resource=$4 out=$5
for path do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path exists.' >&2; exit 2; }
jobs=${CROSS_JOBS:-2}
case "$jobs" in ''|0|*[!0-9]*) exit 2;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || exit 2
ports=$(CDPATH= cd "$(dirname "$0")/../.." && pwd -P)
recipe=$ports/pkgsrc/local-robotics/rtabmap
[ "$("$tools/bin/aarch64--netbsd-clang++" -dumpversion)" = 23.1.4 ]
case "$("$tools/bin/aarch64--netbsd-clang++" -dumpmachine)" in aarch64-unknown-netbsd*|aarch64--netbsd*) ;; *) exit 2;; esac
[ -x "$resource" ] || { echo 'Build the genuine native resource tool first.' >&2; exit 2; }
printf '%s  %s\n' 587d8936b8d8669b196d500df80e373417e0c4c033309a2e4a0b84a627117284 "$archive" | sha256sum -c -
[ -f "$sysroot/usr/pkg/llvm/lib/libc++.so.1" ] || { echo 'Missing target libc++ runtime.' >&2; exit 2; }
for config in lib/cmake/opencv5/OpenCVConfig.cmake share/pcl-1.15/PCLConfig.cmake lib/cmake/GTSAM/GTSAMConfig.cmake; do
    [ -f "$sysroot/usr/pkg/$config" ] || { echo "Missing dependency: $config" >&2; exit 2; }
done
[ -f "$sysroot/usr/pkg/lib/libsqlite3.so" ]
unset COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
PKG_CONFIG_SYSROOT_DIR=$sysroot PKG_CONFIG_LIBDIR=$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/lib/pkgconfig PKG_CONFIG_PATH=
export PKG_CONFIG_SYSROOT_DIR PKG_CONFIG_LIBDIR PKG_CONFIG_PATH
mkdir -p "$out/source" "$out/logs"
sha256sum "$archive" "$recipe/features.cmake" "$0" > "$out/inputs.sha256"
tar -xf "$archive" --strip-components=1 -C "$out/source"
for name in patch-opencv5-upstream patch-shared-dependencies patch-gtsam-optional patch-relocatable-exports patch-private-lz4-symbols; do
    [ -f "$recipe/patches/$name" ] || { echo "Missing canonical patch: $name" >&2; exit 1; }
done
for delta in "$recipe/patches/"patch-*; do
    sha256sum "$delta" >> "$out/inputs.sha256"
    patch --batch --forward -F 0 -d "$out/source" -p1 < "$delta" >> "$out/logs/patches.log" 2>&1
done
cat > "$out/toolchain.cmake" <<CMAKE
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $tools/bin/aarch64--netbsd-clang)
set(CMAKE_CXX_COMPILER $tools/bin/aarch64--netbsd-clang++)
set(CMAKE_C_FLAGS_INIT "-march=armv8-a")
set(CMAKE_CXX_FLAGS_INIT "-march=armv8-a")
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
    -DRTABMAP_RES_TOOL="$resource" \
    -DEigen3_DIR="$sysroot/usr/pkg/share/eigen3/cmake" \
    -DOpenCV_DIR="$sysroot/usr/pkg/lib/cmake/opencv5" -DPCL_DIR="$sysroot/usr/pkg/share/pcl-1.15" \
    -DGTSAM_DIR="$sysroot/usr/pkg/lib/cmake/GTSAM" \
    -DSQLite3_INCLUDE_DIR="$sysroot/usr/pkg/include" -DSQLite3_LIBRARY="$sysroot/usr/pkg/lib/libsqlite3.so" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/llvm/lib' > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel "$jobs" > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
sh "$recipe/files/install-licenses.sh" "$out/source" "$out/stage/usr/pkg" "$recipe"
find "$out/stage/usr/pkg/lib" -type f -name '*.so*' -exec "$tools/bin/aarch64--netbsd-readelf" -h -d {} + > "$out/elf.txt"
[ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 2 ]
for path in "$tools" "$sysroot" "$out"; do
    if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$path"; then exit 1; fi
    if grep -R -F "$path" "$out/stage/usr/pkg/lib/rtabmap-0.23"; then
        echo 'Build-host path leaked into installed CMake exports.' >&2; exit 1
    fi
done
(cd "$out/stage/usr/pkg" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/files.txt"
echo "Staged RTAB-Map: $out/stage/usr/pkg"
