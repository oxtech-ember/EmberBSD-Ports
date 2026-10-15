#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). One headless OpenCV provider for recorded RGB-D.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: cross-opencv.sh GCC_PREFIX SYSROOT ARCHIVE NEW_OUTPUT' >&2; exit 2; }
compiler=$1 sysroot=$2 archive=$3 out=$4
for path do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
jobs=${CROSS_JOBS:-2}
case "$jobs" in ''|0|*[!0-9]*) exit 2;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || exit 2
ports=$(CDPATH= cd "$(dirname "$0")/../.." && pwd -P)
recipe=$ports/pkgsrc/local-robotics/opencv5
[ "$("$compiler/bin/aarch64--netbsd-g++" -dumpfullversion)" = 16.2.0 ]
printf '%s  %s\n' b0528f5a1d379d59d4701cb28c36e22214cc51cf64594e5b56f2d3e6c0233095 "$archive" | sha256sum -c -
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
for file in "$crt/crtbeginS.o" "$runtime/libstdc++.so.7" "$sysroot/usr/pkg/lib/libpng16.so" "$sysroot/usr/pkg/lib/libjpeg.so"; do
    [ -f "$file" ] || { echo "Missing dependency: $file" >&2; exit 2; }
done
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
PKG_CONFIG_SYSROOT_DIR=$sysroot PKG_CONFIG_LIBDIR=$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/lib/pkgconfig PKG_CONFIG_PATH=
export PKG_CONFIG_SYSROOT_DIR PKG_CONFIG_LIBDIR PKG_CONFIG_PATH
mkdir -p "$out/source" "$out/logs"
sha256sum "$archive" "$recipe/features.cmake" "$0" > "$out/inputs.sha256"
tar -xf "$archive" --strip-components=1 -C "$out/source"
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
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -march=armv8-a -Wl,-rpath,/usr/pkg/gcc16/lib -isystem $headers -isystem $headers/aarch64--netbsd -isystem $headers/backward")
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
    -DWITH_OBSENSOR=OFF \
    -DEigen3_DIR="$sysroot/usr/pkg/share/eigen3/cmake" \
    -DJPEG_INCLUDE_DIR="$sysroot/usr/pkg/include" -DJPEG_LIBRARY_RELEASE="$sysroot/usr/pkg/lib/libjpeg.so" \
    -DPNG_PNG_INCLUDE_DIR="$sysroot/usr/pkg/include" -DPNG_LIBRARY_RELEASE="$sysroot/usr/pkg/lib/libpng16.so" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel "$jobs" > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
sh "$recipe/files/install-licenses.sh" "$out/source" "$out/stage/usr/pkg" "$recipe"
find "$out/stage/usr/pkg/lib" -type f -name '*.so*' -exec "$compiler/bin/aarch64--netbsd-readelf" -h -d {} + > "$out/elf.txt"
if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$out"; then exit 1; fi
(cd "$out/stage/usr/pkg" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/files.txt"
echo "Staged OpenCV: $out/stage/usr/pkg"
