#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Current shared XML cross dependency.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: build-libxml2.sh GCC_PREFIX SYSROOT ARCHIVE NEW_OUTPUT' >&2; exit 2; }
prefix=$1 sysroot=$2 archive=$3 out=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
cross=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
recipe=$cross/../recipes/textproc/libxml2
for compiler in gcc g++; do
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpfullversion)" = 16.2.0 ]
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpmachine)" = aarch64--netbsd ]
done
expected=$(awk '$1 == "libxml2-2.15.4" {print $3}' "$cross/dependencies.tsv")
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
set -- "$recipe/patches/"patch-*
[ "$#" = "$(grep -c '^SHA1 (patch-' "$recipe/distinfo")" ]
for patch_file do
    name=$(basename "$patch_file")
    expected=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name {print $4}' "$recipe/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$patch_file" | sha1sum | awk '{print $1}')
    [ -n "$expected" ] && [ "$expected" = "$actual" ] || exit 1
done
(cd "$recipe/files" && sha256sum -c test-support.sha256)
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
[ -f "$crt/crtbeginS.o" ] && [ -f "$runtime/libgcc_s.so.1" ] || exit 1
[ -f "$sysroot/usr/include/stdio.h" ]
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
mkdir -p "$out/source" "$out/logs" "$out/recipe"
sha256sum "$archive" "$cross/dependencies.tsv" "$recipe/distinfo" "$recipe/patches/"patch-* \
    "$recipe/files/"* "$0" > "$out/inputs.sha256"
tar -xf "$archive" --strip-components=1 -C "$out/source"
cp "$recipe/files/"*.cmake "$out/source/"
for patch_file in "$recipe/patches/"patch-*; do
    patch -f -F0 -p0 -d "$out/source" < "$patch_file" > "$out/logs/$(basename "$patch_file").log" 2>&1
done
cat > "$out/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $prefix/bin/aarch64--netbsd-gcc)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
# Keep upstream CMake defaults, programs and all upstream tests. The Python
# language binding is a separate package, not a dependency of the C interface.
cmake -S "$out/source" -B "$out/build" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr/pkg -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBUILD_SHARED_LIBS=ON \
    -DLIBXML2_WITH_PYTHON=OFF -DLIBXML2_WITH_TESTS=ON \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' \
    > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel "${CROSS_JOBS:-4}" > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
licenses=$out/stage/usr/pkg/share/licenses/libxml2
mkdir -p "$licenses"
cp "$out/source/Copyright" "$licenses/Copyright"
cp "$cross/dependencies.tsv" "$licenses/SOURCE"
for source in dict.c list.c; do
    sed -n '1,/^ \*\//p' "$out/source/$source" > "$licenses/$source-notice.txt"
done
chmod 644 "$licenses/"*
mkdir "$out/consumer"
"$prefix/bin/aarch64--netbsd-gcc" --sysroot="$sysroot" -B"$crt/" -L"$runtime" \
    -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
    -I"$out/stage/usr/pkg/include/libxml2" -L"$out/stage/usr/pkg/lib" \
    -Wl,-rpath,/usr/pkg/lib -Wl,-rpath,/usr/pkg/gcc16/lib \
    "$cross/../tests/libxml2-options.c" -lxml2 -o "$out/consumer/libxml2-options" \
    > "$out/logs/consumer-build.log" 2>&1
"$prefix/bin/aarch64--netbsd-gcc" --sysroot="$sysroot" -B"$crt/" -L"$runtime" \
    -std=c11 -O2 -Wall -Wextra -Wpedantic \
    -I"$out/stage/usr/pkg/include/libxml2" -L"$out/stage/usr/pkg/lib" \
    -Wl,-rpath,/usr/pkg/lib -Wl,-rpath,/usr/pkg/gcc16/lib \
    "$cross/../../../probes/libxml2/tests/contract.c" -lxml2 -o "$out/consumer/xml-contract" \
    > "$out/logs/xml-contract-build.log" 2>&1
(cd "$out/stage/usr/pkg" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/recipe/PLIST"
printf '%s\n' 'Current libxml2 C interface, shared library, development exports and XML programs.' \
    'This cross payload uses upstream CMake defaults. The native pkgsrc payload uses Autotools.' \
    > "$out/recipe/DESCR"
"$prefix/bin/aarch64--netbsd-readelf" -h -d "$out/stage/usr/pkg/lib/libxml2.so.16.1.4" \
    "$out/stage/usr/pkg/bin/xmllint" "$out/stage/usr/pkg/bin/xmlcatalog" \
    "$out/consumer/libxml2-options" "$out/consumer/xml-contract" > "$out/elf.txt"
[ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 5 ]
for path in "$prefix" "$sysroot" "$out"; do
    if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$path"; then
        echo 'Build-host path leaked into target linkage.' >&2; exit 1
    fi
done
echo "Staged current XML dependency: $out/stage/usr/pkg"
