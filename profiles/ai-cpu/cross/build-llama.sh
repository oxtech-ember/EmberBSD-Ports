#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), GCC16 cross-build and staged CPU installation.
set -eu
umask 022
test "$#" = 4 || { echo 'Usage: build-llama.sh CROSS_PREFIX SYSROOT ARCHIVE NEW_OUTPUT' >&2; exit 2; }
prefix=$1 sysroot=$2 archive=$3 out=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
test ! -e "$out" && test ! -L "$out" || { echo 'Output already exists.' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
recipe=$root/pkgsrc/local-ai/llama-cpp
cc=$prefix/bin/aarch64--netbsd-gcc
cxx=$prefix/bin/aarch64--netbsd-g++
test "$("$cc" -dumpfullversion)" = 16.2.0
test "$("$cxx" -dumpfullversion)" = 16.2.0
test "$("$cc" -dumpmachine)" = aarch64--netbsd
test "$("$cxx" -dumpmachine)" = aarch64--netbsd
test -f "$sysroot/usr/include/stdio.h"
test -f "$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/crtbeginS.o"
test -f "$sysroot/usr/pkg/gcc16/lib/libstdc++.so.7"
expected=$(awk '/^Archive SHA256:/ { print $3 }' "$recipe/files/SOURCE")
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
mkdir -p "$out/source" "$out/logs" "$out/stage/usr/pkg/bin" \
    "$out/stage/usr/pkg/share/licenses/llama-cpp" "$out/stage/usr/pkg/share/doc/llama-cpp"
tar -xf "$archive" --strip-components=1 -C "$out/source"
for patch in "$recipe/patches/"patch-*; do
    test -f "$patch"
    name=$(basename "$patch")
    expected=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$recipe/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$patch" | sha1sum | awk '{ print $1 }')
    test -n "$expected" && test "$expected" = "$actual"
    patch -f -N -F 0 -p0 -d "$out/source" < "$patch"
done
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
cxx_headers=$sysroot/usr/pkg/gcc16/include/c++
cat > "$out/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $cc)
set(CMAKE_CXX_COMPILER $cxx)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib")
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib -isystem $cxx_headers -isystem $cxx_headers/aarch64--netbsd -isystem $cxx_headers/backward")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
revision=$(awk '/^Revision:/ { print $2 }' "$recipe/files/SOURCE")
cmake=${CMAKE:-cmake}
"$cmake" -S "$out/source" -B "$out/build" -G Ninja \
    -C "$root/pkgsrc/local-ai/cpu.cmake" -C "$recipe/package.cmake" \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_INSTALL_PREFIX=/usr/pkg \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DLLAMA_BUILD_COMMIT="$revision" \
    -DGGML_CPU_ARM_ARCH=armv8-a -DLLAMA_BUILD_TESTS=ON > "$out/logs/configure.log" 2>&1
programs=$(awk '/^bin\// { sub(/^bin\//, ""); print }' "$recipe/PLIST")
tests='test-sampling test-grammar-parser test-grammar-integration test-json-schema-to-grammar test-gguf test-quantize-fns'
"$cmake" --build "$out/build" -j "${CROSS_JOBS:-4}" --target $programs $tests > "$out/logs/build.log" 2>&1
for program in $programs; do
    cp "$out/build/bin/$program" "$out/stage/usr/pkg/bin/"
    chmod 755 "$out/stage/usr/pkg/bin/$program"
done
cp "$out/source/LICENSE" "$recipe/files/THIRD-PARTY-NOTICES" \
    "$out/stage/usr/pkg/share/licenses/llama-cpp/"
cp "$out/source/vendor/cpp-httplib/LICENSE" "$out/stage/usr/pkg/share/licenses/llama-cpp/vendor_cpp-httplib_LICENSE"
cp "$recipe/files/SOURCE" "$out/stage/usr/pkg/share/doc/llama-cpp/"
chmod 644 "$out/stage/usr/pkg/share/licenses/llama-cpp/"* \
    "$out/stage/usr/pkg/share/doc/llama-cpp/"*
"$prefix/bin/aarch64--netbsd-readelf" -h -l -d "$out/stage/usr/pkg/bin/"* > "$out/elf.txt"
test "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 5
for path in "$prefix" "$sysroot" "$out"; do
    if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$path"; then
        echo 'Build-host path leaked into ELF dependencies.' >&2; exit 1
    fi
done
(cd "$out/stage/usr/pkg" && find . -type f -print | LC_ALL=C sort) > "$out/installed-files.txt"
printf '%s\n' "Staged llama.cpp: $out/stage/usr/pkg; execute target acceptance on EmberBSD."
