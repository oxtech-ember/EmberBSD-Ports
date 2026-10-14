#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Shared OSQP package and installed consumers.
set -eu
umask 022
[ "$#" = 5 ] || { echo 'Usage: cross-build.sh GCC_PREFIX SYSROOT OSQP_ARCHIVE QDLDL_ARCHIVE NEW_OUTPUT' >&2; exit 2; }
prefix=$1 sysroot=$2 osqp=$3 qdldl=$4 out=$5
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ]
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
recipe=$ports/pkgsrc/local-robotics/osqp
for compiler in gcc g++; do
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpfullversion)" = 16.2.0 ]
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpmachine)" = aarch64--netbsd ]
done
expected=$(awk '$1 == "osqp-1.0.0.tar.gz" {print $2}' "$ports/probes/osqp/sources.tsv")
printf '%s  %s\n' "$expected" "$osqp" | sha256sum -c -
expected=$(awk '$1 == "qdldl-0.1.9.tar.gz" {print $2}' "$ports/probes/osqp/sources.tsv")
printf '%s  %s\n' "$expected" "$qdldl" | sha256sum -c -
patch_file=$recipe/patches/patch-src_CMakeLists.txt
expected=$(awk '$1 == "SHA1" && $2 == "(patch-src_CMakeLists.txt)" {print $4}' "$recipe/distinfo")
actual=$(sed '/[$]NetBSD.*/d' "$patch_file" | sha1sum | awk '{print $1}')
[ -n "$expected" ] && [ "$expected" = "$actual" ]
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
[ -f "$crt/crtbeginS.o" ] && [ -f "$runtime/libgcc_s.so.1" ]
[ -f "$sysroot/usr/include/stdio.h" ]
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
mkdir -p "$out/source" "$out/qdldl" "$out/logs"
sha256sum "$osqp" "$qdldl" "$patch_file" "$recipe/features.cmake" "$0" > "$out/inputs.sha256"
tar -xf "$osqp" --strip-components=1 -C "$out/source"
tar -xf "$qdldl" --strip-components=1 -C "$out/qdldl"
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
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_INSTALL_PREFIX=/usr/pkg -DOSQP_VERSION=1.0.0 \
    -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' \
    -DFETCHCONTENT_SOURCE_DIR_QDLDL="$out/qdldl" \
    -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DFETCHCONTENT_UPDATES_DISCONNECTED=ON \
    > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel "${CROSS_JOBS:-4}" > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
licenses=$out/stage/usr/pkg/share/licenses/osqp
mkdir -p "$licenses"
cp "$out/source/LICENSE" "$licenses/OSQP-Apache-2.0"
cp "$out/source/NOTICE" "$licenses/OSQP-NOTICE"
cp "$out/qdldl/LICENSE" "$licenses/QDLDL-Apache-2.0"
cp "$out/source/algebra/_common/lin_sys/qdldl/amd/LICENSE" "$licenses/AMD-BSD-3-Clause"
cp "$recipe/files/SOURCE" "$licenses/SOURCE"
chmod 644 "$licenses/"*
cmake -S "$ports/probes/osqp/tests" -B "$out/consumer" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DPROBE_PREFIX="$out/stage/usr/pkg" \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' \
    > "$out/logs/consumer-configure.log" 2>&1
cmake --build "$out/consumer" --parallel 2 > "$out/logs/consumer-build.log" 2>&1
"$prefix/bin/aarch64--netbsd-readelf" -h -d "$out/stage/usr/pkg/lib/libosqp.so" \
    "$out/consumer/osqp-contract" "$out/consumer/osqp-interrupt" > "$out/elf.txt"
[ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 3 ]
for path in "$prefix" "$sysroot" "$out"; do
    if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$path"; then
        echo 'Build-host path leaked into target linkage.' >&2; exit 1
    fi
done
(cd "$out/stage/usr/pkg" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/files.txt"
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$out/expected-files.txt"
cmp "$out/files.txt" "$out/expected-files.txt"
echo "Staged target OSQP package: $out/stage/usr/pkg"
