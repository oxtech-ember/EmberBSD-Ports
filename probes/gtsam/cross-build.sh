#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). GCC16 shared GTSAM cross package.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: cross-build.sh GCC_PREFIX SYSROOT SOURCE_ARCHIVE NEW_OUTPUT' >&2; exit 2; }
compiler=$1 sysroot=$2 archive=$3 out=$4
for path do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple absolute paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
jobs=${CROSS_JOBS:-3}
case "$jobs" in ''|*[!0-9]*) exit 2;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || exit 2
ports=$(CDPATH= cd "$(dirname "$0")/../.." && pwd -P)
recipe=$ports/pkgsrc/local-robotics/gtsam
for language in gcc g++; do
    [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpfullversion)" = 16.2.0 ]
    [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpmachine)" = aarch64--netbsd ]
done
expected=$(awk '$1=="gtsam-4.3.0.tar.gz" {print $2}' "$ports/probes/gtsam/sources.tsv")
[ "${#expected}" = 64 ] || exit 2
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
[ -f "$crt/crtbeginS.o" ] && [ -f "$runtime/libstdc++.so.7" ]
[ -f "$sysroot/usr/pkg/share/eigen3/cmake/Eigen3Config.cmake" ]
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
mkdir -p "$out/source" "$out/logs"
sha256sum "$archive" "$recipe/features.cmake" "$0" > "$out/inputs.sha256"
tar -xf "$archive" --strip-components=1 -C "$out/source"
cat > "$out/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $compiler/bin/aarch64--netbsd-gcc)
set(CMAKE_CXX_COMPILER $compiler/bin/aarch64--netbsd-g++)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$runtime -march=armv8-a -Wl,-rpath,/usr/pkg/gcc16/lib")
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -march=armv8-a -Wl,-rpath,/usr/pkg/gcc16/lib -isystem $headers -isystem $headers/aarch64--netbsd -isystem $headers/backward")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
cmake -S "$out/source" -B "$out/build" -G Ninja -C "$recipe/features.cmake" \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_EXTENSIONS=OFF \
    -DCMAKE_INSTALL_PREFIX=/usr/pkg -DCMAKE_INSTALL_LIBDIR=lib \
    -DEigen3_DIR="$sysroot/usr/pkg/share/eigen3/cmake" \
    -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' \
    > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --target gtsam CppUnitLite --parallel "$jobs" > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
sh "$ports/probes/gtsam/install-licenses.sh" "$out/source" "$out/stage/usr/pkg" "$recipe"
cmake -S "$ports/probes/gtsam/tests" -B "$out/consumer" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DPROBE_PREFIX="$out/stage/usr/pkg" \
    -DEIGEN_PREFIX="$sysroot/usr/pkg" -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' > "$out/logs/consumer-configure.log" 2>&1
cmake --build "$out/consumer" --parallel 2 > "$out/logs/consumer-build.log" 2>&1
"$compiler/bin/aarch64--netbsd-readelf" -h -d "$out/stage/usr/pkg/lib/libgtsam.so" \
    "$out/stage/usr/pkg/lib/libcephes-gtsam.so" \
    "$out/consumer/gtsam-contract" "$out/consumer/gtsam-matrix-check" > "$out/elf.txt"
[ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 4 ]
for path in "$compiler" "$sysroot" "$out"; do
    if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$path"; then
        echo 'Build-host runtime path leaked.' >&2; exit 1
    fi
    if grep -F "$path" "$out/stage/usr/pkg/lib/cmake/GTSAM/"GTSAM-exports*.cmake; then
        echo 'Build-host path leaked into installed imported targets.' >&2; exit 1
    fi
done
(cd "$out/stage/usr/pkg" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/files.txt"
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$out/expected-files.txt"
cmp "$out/files.txt" "$out/expected-files.txt"
echo "Staged GTSAM: $out/stage/usr/pkg"
