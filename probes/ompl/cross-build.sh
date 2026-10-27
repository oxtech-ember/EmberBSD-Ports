#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Linux GCC16 cross build and staged consumer.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: cross-build.sh GCC_PREFIX SYSROOT OMPL_ARCHIVE NEW_OUTPUT' >&2; exit 2; }
prefix=$1 sysroot=$2 archive=$3 out=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
recipe=$ports/pkgsrc/local-robotics/ompl
jobs=${CROSS_JOBS:-4}
case "$jobs" in ''|*[!0-9]*) exit 2;; esac
[ "$jobs" -gt 0 ] || exit 2
for compiler in gcc g++; do
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpfullversion)" = 16.2.0 ]
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpmachine)" = aarch64--netbsd ]
done
# Eigen and Boost come from the common math/eigen3, devel/boost-headers and
# devel/boost-libs packages installed in the sysroot.
for file in share/eigen3/cmake/Eigen3Config.cmake include/boost/version.hpp \
    lib/cmake/Boost-1.92.0/BoostConfig.cmake lib/libboost_serialization.so \
    lib/libboost_program_options.so lib/libboost_unit_test_framework.so; do
    [ -f "$sysroot/usr/pkg/$file" ] || {
        echo "Missing common package file in the sysroot: $file" >&2; exit 2;
    }
done
expected=$(awk '$1 == "ompl-2.0.2.tar.gz" {print $2}' "$ports/probes/ompl/sources.tsv")
[ "${#expected}" = 64 ] || { echo 'Missing source digest.' >&2; exit 2; }
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
patch_file=$recipe/patches/patch-pkgconfig
expected=$(awk '$1 == "SHA1" && $2 == "(patch-pkgconfig)" {print $4}' "$recipe/distinfo")
actual=$(sed '/[$]NetBSD.*/d' "$patch_file" | sha1sum | awk '{print $1}')
[ -n "$expected" ] && [ "$actual" = "$expected" ] || { echo 'Patch checksum mismatch.' >&2; exit 2; }
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
[ -f "$crt/crtbeginS.o" ] && [ -f "$runtime/libstdc++.so.7" ]
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
mkdir -p "$out/source" "$out/logs"
sha256sum "$archive" "$patch_file" "$recipe/features.cmake" "$0" > "$out/inputs.sha256"
tar -xf "$archive" --strip-components=1 -C "$out/source"
patch -f -F0 -p0 -d "$out/source" < "$patch_file" > "$out/logs/patch.log" 2>&1
cat > "$out/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $prefix/bin/aarch64--netbsd-gcc)
set(CMAKE_CXX_COMPILER $prefix/bin/aarch64--netbsd-g++)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib")
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib -isystem $headers -isystem $headers/aarch64--netbsd -isystem $headers/backward")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
cmake -S "$out/source" -B "$out/build" -G Ninja -C "$recipe/features.cmake" \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr/pkg -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_PREFIX_PATH="$sysroot/usr/pkg" -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON \
    -DCMAKE_PROJECT_ompl_INCLUDE="$ports/probes/ompl/dependencies.cmake" \
    -DEIGEN_PREFIX="$sysroot/usr/pkg" -DBOOST_PREFIX="$sysroot/usr/pkg" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' \
    > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel "$jobs" > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
mkdir -p "$out/stage/usr/pkg/share/licenses/ompl"
cp "$out/source/LICENSE" "$recipe/files/SOURCE" "$out/stage/usr/pkg/share/licenses/ompl/"
sh "$ports/probes/ompl/tests/pkgconfig-contract.sh" "$out/stage/usr/pkg" "$sysroot" > "$out/logs/pkgconfig.log" 2>&1
cmake -S "$ports/probes/ompl/tests" -B "$out/consumer" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON \
    -DPROBE_PREFIX="$out/stage/usr/pkg" -DEIGEN_PREFIX="$sysroot/usr/pkg" \
    -DBOOST_PREFIX="$sysroot/usr/pkg" -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' \
    > "$out/logs/consumer-configure.log" 2>&1
cmake --build "$out/consumer" --parallel 2 > "$out/logs/consumer-build.log" 2>&1
"$prefix/bin/aarch64--netbsd-readelf" -h -d "$out/stage/usr/pkg/lib/libompl.so" \
    "$out/consumer/ompl-contract" "$out/consumer/geometry-contract" > "$out/elf.txt"
[ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 3 ]
for path in "$prefix" "$sysroot" "$out"; do
    if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$path"; then
        echo 'Build-host path leaked into target linkage.' >&2; exit 1
    fi
done
(cd "$out/stage/usr/pkg" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/files.txt"
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$out/expected-files.txt"
cmp "$out/files.txt" "$out/expected-files.txt"
echo "Staged target OMPL package: $out/stage/usr/pkg"
