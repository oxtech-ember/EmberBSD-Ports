#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Reuse canonical PNG and JPEG provider recipes.
set -eu
umask 022
[ "$#" = 7 ] || { echo 'Usage: build.sh native|cross GCC_PREFIX SYSROOT|- PREFIX ARCHIVES JPEG_RECIPE NEW_WORK' >&2; exit 2; }
mode=$1 compiler=$2 sysroot=$3 prefix=$4 archives=$5 jpeg_recipe=$6 out=$7
case "$mode" in native|cross) ;; *) exit 2;; esac
for path in "$compiler" "$prefix" "$archives" "$jpeg_recipe" "$out"; do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Work path already exists.' >&2; exit 2; }
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
ports=$(CDPATH= cd "$recipe/../../.." && pwd -P)
png_recipe=$ports/profiles/common-graphics/recipes/graphics/png
jobs=${CODECS_JOBS:-2}
case "$jobs" in 1|2) ;; *) echo 'Use one or two jobs.' >&2; exit 2;; esac
for tool in ruby patch tar make cmake ninja sha256sum; do command -v "$tool" >/dev/null; done
while read -r name expected url; do
    printf '%s  %s\n' "$expected" "$archives/$name" | sha256sum -c -
done < "$recipe/sources.tsv"
grep -F 'DISTNAME=' "$png_recipe/Makefile" | grep -F 'libpng-1.6.59' >/dev/null
grep -F 'DISTNAME=' "$jpeg_recipe/Makefile" | grep -F 'libjpeg-turbo-3.2.0' >/dev/null
grep -E '^PKGREVISION=[[:space:]]*2$' "$jpeg_recipe/Makefile" >/dev/null
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
if [ "$mode" = cross ]; then
    case "$sysroot" in /*) ;; *) exit 2;; esac
    [ "$prefix" = /usr/pkg ] || exit 2
    cc=$compiler/bin/aarch64--netbsd-gcc
    cxx=$compiler/bin/aarch64--netbsd-g++
    [ "$("$cc" -dumpmachine)" = aarch64--netbsd ]
    crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
    flags="--sysroot=$sysroot -B$crt/ -march=armv8-a -O2"
    linkflags='-Wl,-rpath,/usr/pkg/gcc16/lib'
    host_args='--host=aarch64--netbsd'
    png_extra=-DPNG_NO_ASSEMBLER_CODE
else
    [ "$sysroot" = - ] || exit 2
    cc=$compiler/bin/gcc cxx=$compiler/bin/g++
    flags=-O2
    linkflags="-Wl,-rpath,$prefix/lib"
    host_args= png_extra=
fi
[ "$("$cc" -dumpfullversion)" = 16.2.0 ]
[ "$("$cxx" -dumpfullversion)" = 16.2.0 ]
mkdir -p "$out/png/source" "$out/png/build" "$out/png/stage" "$out/jpeg/source" "$out/jpeg/stage" "$out/logs"
df -B1 "$out" > "$out/logs/disk-start.txt"
sha256sum "$recipe/build.sh" "$recipe/sources.tsv" "$png_recipe/Makefile" "$png_recipe/distinfo" "$jpeg_recipe/Makefile" "$jpeg_recipe/distinfo" > "$out/logs/inputs.sha256"
tar -xf "$archives/libpng-1.6.59.tar.xz" --strip-components=1 -C "$out/png/source"
tar -xf "$archives/libjpeg-turbo-3.2.0.tar.gz" --strip-components=1 -C "$out/jpeg/source"
for component in png jpeg; do
    if [ "$component" = png ]; then owner=$png_recipe; else owner=$jpeg_recipe; fi
    for file in "$owner"/patches/patch-*; do
        expected=$(awk -v name="$(basename "$file")" '$1=="SHA1" && $2=="("name")" {print $4}' "$owner/distinfo")
        [ "${#expected}" = 40 ]
        # pkgsrc patch checksums exclude expanded NetBSD RCS identifier lines.
        actual=$(sed '/\$NetBSD.*\$/d' "$file" | sha1sum | awk '{print $1}')
        [ "$actual" = "$expected" ] || { echo "Patch checksum mismatch: $file" >&2; exit 2; }
        printf '%s  %s\n' "$actual" "$file" >> "$out/logs/patches.log"
        patch -d "$out/$component/source" -p0 < "$file" >> "$out/logs/patches.log"
    done
done
# This substitutes the canonical pkgsrc SUBST_VARS value before configure.
sed 's|@COMPILER_RPATH_FLAG@|-Wl,-rpath,|g' "$out/png/source/libpng-config.in" > "$out/png/source/libpng-config.in.new"
mv "$out/png/source/libpng-config.in.new" "$out/png/source/libpng-config.in"
export CODECS_COMPDB_LOG=$out/png/compiler.jsonl
export CC="ruby $recipe/record-compiler.rb $cc"
export CFLAGS="$flags" LDFLAGS="$linkflags"
export CPPFLAGS="-DPNG_USER_CHUNK_CACHE_MAX=128 -DPNG_USER_CHUNK_MALLOC_MAX=8000000 $png_extra"
if [ "$mode" = cross ]; then
    AR=$compiler/bin/aarch64--netbsd-ar RANLIB=$compiler/bin/aarch64--netbsd-ranlib
    export AR RANLIB
fi
(cd "$out/png/build" && "$out/png/source/configure" --prefix="$prefix" --mandir="$prefix/man" --disable-unversioned-links $host_args) > "$out/logs/png-configure.log" 2>&1
make -C "$out/png/build" -j"$jobs" > "$out/logs/png-build.log" 2>&1
make -C "$out/png/build" install install-header-links DESTDIR="$out/png/stage" > "$out/logs/png-install.log" 2>&1
ruby -rjson -e 'rows=File.readlines(ARGV[0]).map { |line| JSON.parse(line) }; File.write(ARGV[1],JSON.pretty_generate(rows)+"\n")' "$out/png/compiler.jsonl" "$out/png/build/compile_commands.json"
unset CC CFLAGS CPPFLAGS LDFLAGS AR RANLIB CODECS_COMPDB_LOG
if [ "$mode" = cross ]; then
    cat > "$out/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $cc)
set(CMAKE_CXX_COMPILER $cxx)
set(CMAKE_C_FLAGS_INIT "$flags $linkflags")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
    toolchain=-DCMAKE_TOOLCHAIN_FILE=$out/toolchain.cmake
    simd=ON
else
    toolchain=
    simd=OFF
fi
cmake -S "$out/jpeg/source" -B "$out/jpeg/build" -G Ninja $toolchain \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER="$cc" -DCMAKE_CXX_COMPILER="$cxx" \
    -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_MANDIR=man \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DWITH_JPEG8=ON -DWITH_SYSTEM_ZLIB=ON \
    -DWITH_SIMD="$simd" -DWITH_TESTS=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;/usr/pkg/gcc16/lib" -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    > "$out/logs/jpeg-configure.log" 2>&1
cmake --build "$out/jpeg/build" --parallel "$jobs" > "$out/logs/jpeg-build.log" 2>&1
DESTDIR="$out/jpeg/stage" cmake --install "$out/jpeg/build" > "$out/logs/jpeg-install.log" 2>&1
for component in png jpeg; do
    if [ "$component" = png ]; then owner=$png_recipe; else owner=$jpeg_recipe; fi
    ruby "$recipe/check-plist.rb" "$component" "$owner" "$out/$component/stage$prefix" "$out/$component/files.txt"
done
echo "Staged $mode PNG and JPEG providers under $out"
