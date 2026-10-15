#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), GCC16 cross-build and staged CPU installation.
set -eu
umask 022
test "$#" = 4 || { echo 'Usage: build-whisper.sh CROSS_PREFIX SYSROOT ARCHIVE NEW_OUTPUT' >&2; exit 2; }
prefix=$1 sysroot=$2 archive=$3 out=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
test ! -e "$out" && test ! -L "$out" || { echo 'Output already exists.' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
recipe=$root/pkgsrc/local-ai/whisper-cpp
cc=$prefix/bin/aarch64--netbsd-gcc
cxx=$prefix/bin/aarch64--netbsd-g++
readelf=$prefix/bin/aarch64--netbsd-readelf
cmake=${CMAKE:-cmake}
ninja=${NINJA:-ninja}
test "$("$cc" -dumpfullversion)" = 16.2.0
test "$("$cxx" -dumpfullversion)" = 16.2.0
test "$("$cc" -dumpmachine)" = aarch64--netbsd
test "$("$cxx" -dumpmachine)" = aarch64--netbsd
test -f "$sysroot/usr/include/stdio.h"
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
cxx_headers=$sysroot/usr/pkg/gcc16/include/c++
test -f "$crt/crtbeginS.o"
test -f "$runtime/libstdc++.so.7"
test -f "$runtime/libgcc_s.so.1"
expected=$(awk '/^Archive SHA256:/ { print $3 }' "$recipe/files/SOURCE")
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
patch_count=0
for patch_file in "$recipe/patches/"patch-*; do
    if test ! -e "$patch_file" && test ! -L "$patch_file"; then continue; fi
    test -f "$patch_file"
    name=$(basename "$patch_file")
    expected=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$recipe/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$patch_file" | sha1sum | awk '{ print $1 }')
    test -n "$expected" && test "$expected" = "$actual"
    patch_count=$((patch_count + 1))
done
test "$patch_count" = "$(awk '$1 == "SHA1" && $2 ~ /^\(patch-/ { count++ } END { print count + 0 }' "$recipe/distinfo")"
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
stage=$out/stage/usr/pkg
mkdir -p "$out/source" "$out/logs" "$stage/bin" \
    "$stage/share/licenses/whisper-cpp" "$stage/share/doc/whisper-cpp"
sha256sum "$archive" "$recipe/Makefile" "$recipe/distinfo" "$recipe/PLIST" \
    "$recipe/files/SOURCE" "$recipe/files/THIRD-PARTY-NOTICES" \
    "$root/pkgsrc/local-ai/cpu.cmake" "$recipe/package.cmake" "$0" > "$out/inputs.sha256"
{
    "$cc" --version
    "$cc" -dumpmachine
    "$cc" -print-sysroot
    "$cc" -print-search-dirs
    "$cxx" --version
    "$cxx" -print-search-dirs
    "$readelf" --version
    "$cmake" --version
    "$ninja" --version
    patch --version
} > "$out/tools.txt" 2>&1
tar -xf "$archive" --strip-components=1 -C "$out/source"
for patch_file in "$recipe/patches/"patch-*; do
    test -f "$patch_file" || continue
    sha256sum "$patch_file" >> "$out/inputs.sha256"
    patch -f -N -F 0 -p0 -d "$out/source" < "$patch_file" \
        > "$out/logs/$(basename "$patch_file").log" 2>&1
done
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
"$cmake" -S "$out/source" -B "$out/build" -G Ninja \
    -C "$root/pkgsrc/local-ai/cpu.cmake" -C "$recipe/package.cmake" \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_INSTALL_PREFIX=/usr/pkg \
    -DCMAKE_MAKE_PROGRAM="$(command -v "$ninja")" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DWHISPER_BUILD_COMMIT="$revision" -DGGML_CPU_ARM_ARCH=armv8-a \
    -DWHISPER_BUILD_TESTS=ON > "$out/logs/configure.log" 2>&1
programs=$(awk '/^bin\// { sub(/^bin\//, ""); print }' "$recipe/PLIST")
test "$(printf '%s\n' "$programs" | wc -l | tr -d ' ')" = 3
tests='test-common-utf8 test-whisper-buffer-loader test-whisper-zero-samples test-whisper-lang-detect-abort'
printf '%s\n' $tests > "$out/upstream-tests.txt"
"$cmake" --build "$out/build" -j "${CROSS_JOBS:-4}" --target $programs $tests \
    > "$out/logs/build.log" 2>&1
for program in $programs; do
    cp "$out/build/bin/$program" "$stage/bin/"
    chmod 755 "$stage/bin/$program"
done
cp "$out/source/LICENSE" "$recipe/files/THIRD-PARTY-NOTICES" "$stage/share/licenses/whisper-cpp/"
cp "$recipe/files/SOURCE" "$stage/share/doc/whisper-cpp/"
chmod 644 "$stage/share/licenses/whisper-cpp/"* "$stage/share/doc/whisper-cpp/"*
sed '/^@comment/d; /^$/d' "$recipe/PLIST" | LC_ALL=C sort > "$out/expected-files.txt"
(cd "$stage" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) \
    > "$out/installed-files.txt"
cmp "$out/expected-files.txt" "$out/installed-files.txt"
(cd "$stage" && find . -printf '%m %p\n' | LC_ALL=C sort) > "$out/installed-modes.txt"
(cd "$stage"
    while IFS= read -r file; do sha256sum "$file"; done < "$out/installed-files.txt"
) > "$out/installed.sha256"
"$readelf" -h -l -d "$stage/bin/"* > "$out/elf.txt"
test "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 3
test "$(grep -c 'Requesting program interpreter: /usr/libexec/ld.elf_so' "$out/elf.txt")" = 3
for target in $tests; do
    "$readelf" -h -l -d "$out/build/bin/$target"
done > "$out/tests-elf.txt"
test "$(grep -c 'Machine:.*AArch64' "$out/tests-elf.txt")" = 4
for path in "$prefix" "$sysroot" "$out"; do
    if grep -h -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" "$out/tests-elf.txt" | grep -F "$path"; then
        echo 'Build-host path leaked into ELF dependencies.' >&2; exit 1
    fi
done
printf '%s\n' "Staged whisper.cpp: $stage; execute target acceptance on EmberBSD."
