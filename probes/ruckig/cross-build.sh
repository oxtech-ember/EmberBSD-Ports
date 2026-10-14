#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Build the package and an installed consumer.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: cross-build.sh GCC_PREFIX SYSROOT ARCHIVE NEW_OUTPUT' >&2; exit 2; }
prefix=$1 sysroot=$2 archive=$3 out=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
recipe=$ports/pkgsrc/local-robotics/ruckig
for compiler in gcc g++; do
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpfullversion)" = 16.2.0 ]
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpmachine)" = aarch64--netbsd ]
done
expected=$(awk '{ print $2 }' "$ports/probes/ruckig/sources.tsv")
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
test -f "$sysroot/usr/pkg/gcc16/lib/libstdc++.so.7"
mkdir -p "$out/source" "$out/logs"
tar -xf "$archive" --strip-components=1 -C "$out/source"
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
cat > "$out/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_CXX_COMPILER $prefix/bin/aarch64--netbsd-g++)
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib -isystem $headers -isystem $headers/aarch64--netbsd -isystem $headers/backward")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
cmake -S "$out/source" -B "$out/build" -G Ninja -C "$recipe/features.cmake" \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_INSTALL_PREFIX=/usr/pkg \
    -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' \
    > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel "${CROSS_JOBS:-4}" > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
mkdir -p "$out/stage/usr/pkg/share/licenses/ruckig"
cp "$out/source/LICENSE" "$recipe/files/SOURCE" "$out/stage/usr/pkg/share/licenses/ruckig/"
chmod 644 "$out/stage/usr/pkg/share/licenses/ruckig/"*
cmake -S "$ports/probes/ruckig/tests" -B "$out/consumer" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DPROBE_PREFIX="$out/stage/usr/pkg" -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' \
    > "$out/logs/consumer-configure.log" 2>&1
cmake --build "$out/consumer" --parallel 2 > "$out/logs/consumer-build.log" 2>&1
"$prefix/bin/aarch64--netbsd-readelf" -h -d "$out/stage/usr/pkg/lib/libruckig.so" \
    "$out/consumer/ruckig-contract" "$out/build/test-target" > "$out/elf.txt"
for path in "$prefix" "$sysroot" "$out"; do
    if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$path"; then
        echo 'Build-host path leaked into target linkage.' >&2; exit 1
    fi
done
(cd "$out/stage/usr/pkg" && find . -type f | sed 's|^\./||' | LC_ALL=C sort) > "$out/files.txt"
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$out/expected-files.txt"
cmp "$out/files.txt" "$out/expected-files.txt"
echo "Staged target Ruckig package: $out/stage/usr/pkg"
