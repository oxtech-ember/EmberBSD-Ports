#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Shared x265 provider for the RTP CPU profile.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: build-x265.sh native|cross ARCHIVES NEW_OUTPUT PREFIX' >&2; exit 2; }
mode=$1 archives=$2 out=$3 prefix=$4
case "$mode" in native|cross) ;; *) exit 2;; esac
for path in "$archives" "$out" "$prefix"; do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Preserve the existing output.' >&2; exit 2; }
jobs=${JOBS:-2}
case "$jobs" in ''|0|*[!0-9]*) exit 2;; esac
profile=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
recipes=$(CDPATH= cd -- "$profile/../../pkgsrc" && pwd -P)
recipe=$recipes/multimedia/x265
archive=$archives/x265_4.2.tar.gz
hash=$(awk '$1=="multimedia/x265"{print $3}' "$profile/sources.tsv")
[ "${#hash}" = 64 ]
printf '%s  %s\n' "$hash" "$archive" | sha256sum -c -
mkdir -p "$out/source" "$out/logs"
tar -xf "$archive" --strip-components=1 -C "$out/source"
sha256sum "$archive" "$recipe/distinfo" "$recipe/Makefile" "$0" > "$out/inputs.sha256"
for file in "$recipe/patches/"patch-*; do
    name=$(basename "$file")
    expected=$(awk -v name="($name)" '$1=="SHA1"&&$2==name{print $4}' "$recipe/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$file" | sha1sum | cut -d' ' -f1)
    [ -n "$expected" ] && [ "$actual" = "$expected" ]
    sha256sum "$file" >> "$out/inputs.sha256"
    patch --fuzz=0 -p0 -d "$out/source/source" < "$file" >> "$out/logs/patch.log" 2>&1
done
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH
if [ "$mode" = cross ]; then
    : "${GCC_PREFIX:?}" "${SYSROOT:?}" "${TARGET:?}"
    case "$TARGET" in aarch64--netbsd) arch=aarch64;; x86_64--netbsd) arch=x86_64;; *) exit 2;; esac
    for language in gcc g++; do
        [ "$("$GCC_PREFIX/bin/$TARGET-$language" -dumpfullversion)" = 16.2.0 ]
        [ "$("$GCC_PREFIX/bin/$TARGET-$language" -dumpmachine)" = "$TARGET" ]
    done
    crt=$SYSROOT/usr/pkg/gcc16/lib/gcc/$TARGET/16.2.0
    runtime=$SYSROOT/usr/pkg/gcc16/lib
    headers=$SYSROOT/usr/pkg/gcc16/include/c++
    [ -f "$crt/crtbeginS.o" ] && [ -f "$runtime/libstdc++.so.7" ]
    cat > "$out/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR $arch)
set(CMAKE_SYSROOT $SYSROOT)
set(CMAKE_C_COMPILER $GCC_PREFIX/bin/$TARGET-gcc)
set(CMAKE_CXX_COMPILER $GCC_PREFIX/bin/$TARGET-g++)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib")
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib -isystem $headers -isystem $headers/$TARGET -isystem $headers/backward")
set(CMAKE_FIND_ROOT_PATH $SYSROOT)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
    set -- -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" \
        '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' -DENABLE_ASSEMBLY=ON
    if [ "$arch" = aarch64 ]; then
        set -- "$@" -DENABLE_NEON_DOTPROD=OFF -DENABLE_NEON_I8MM=OFF \
            -DENABLE_SVE=OFF -DENABLE_SVE2=OFF -DENABLE_SVE2_BITPERM=OFF
    fi
else
    . "$profile/../common-build-tools/cross/host-gcc16.sh"
    ember_require_host_gcc16 HOST_CC c
    ember_require_host_gcc16 HOST_CXX c++
    [ "$("$HOST_CC" -dumpfullversion)" = 16.2.0 ]
    [ "$("$HOST_CXX" -dumpfullversion)" = 16.2.0 ]
    set -- -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
        "-DCMAKE_INSTALL_RPATH=$prefix/lib;/usr/local/lib64" -DENABLE_ASSEMBLY=OFF
fi
cmake -S "$out/source/source" -B "$out/build" -G Ninja "$@" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DENABLE_PIC=ON -DENABLE_SHARED=ON -DENABLE_CLI=ON -DENABLE_TESTS=ON \
    -DENABLE_LIBNUMA=OFF -DX265_VERSION=4.2 -DX265_LATEST_TAG=4.2 \
    > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel "$jobs" > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
stage=$out/stage$prefix
mkdir -p "$stage/share/licenses/x265"
cp "$out/source/COPYING" "$stage/share/licenses/x265/COPYING"
(cd "$stage" && find . \( -type f -o -type l \) -print | sed 's|^./||' | LC_ALL=C sort) > "$out/files.txt"
if [ "$mode" = native ]; then
    mkdir -p "$prefix"
    cp -a "$stage/." "$prefix/"
fi
printf 'Staged x265 4.2 (%s): %s\n' "$mode" "$stage"
