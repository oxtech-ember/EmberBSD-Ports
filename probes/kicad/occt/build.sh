#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build a core contract or the complete KiCad dependency.
set -eu
[ "$#" -ge 5 ] && [ "$#" -le 6 ] || { echo 'Usage: build.sh MODE SOURCE NEW_BUILD NEW_STAGE PREFIX [TARGET_TOOLCHAIN]' >&2; exit 2; }
mode=$1 source=$2 build=$3 stage=$4 prefix=$5
shift 5
case "$mode" in native-core|native-full|cross-full) ;; *) exit 2;; esac
for path in "$source" "$build" "$stage" "$prefix"; do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./+-]*) exit 2;; esac
done
[ ! -e "$build" ] && [ ! -L "$build" ] || exit 2
[ ! -e "$stage" ] && [ ! -L "$stage" ] || exit 2
jobs=${JOBS:-1}
case "$jobs" in 1|2) ;; *) echo 'JOBS must be 1 or 2' >&2; exit 2;; esac
if [ "$mode" = cross-full ]; then
    [ "$#" -eq 1 ] || exit 2
    toolchain=$1
    case "$toolchain" in /*) ;; *) exit 2;; esac
    set -- "-DCMAKE_TOOLCHAIN_FILE=$toolchain"
    unset LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH
else
    [ "$#" -eq 0 ] || exit 2
    set --
fi
if [ "$mode" = native-core ]; then
    set -- "$@" -DBUILD_MODULE_Draw=OFF -DBUILD_MODULE_ModelingData=OFF -DBUILD_MODULE_ModelingAlgorithms=OFF \
        -DBUILD_MODULE_Visualization=OFF -DBUILD_MODULE_ApplicationFramework=OFF -DBUILD_MODULE_DataExchange=OFF
else
    set -- "$@" -DBUILD_MODULE_Draw=ON -DUSE_TK=ON -DUSE_FREEIMAGE=ON \
        -DUSE_FREETYPE=ON -DUSE_EIGEN=ON -DUSE_RAPIDJSON=ON -DUSE_XLIB=ON -DUSE_OPENGL=ON
fi
mkdir -p "$build" "$stage"
cmake -S "$source" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_EXPORT_PACKAGE_REGISTRY=OFF \
    -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON \
    -DBUILD_RELEASE_DISABLE_EXCEPTIONS=OFF -DBUILD_USE_PCH=OFF \
    -DBUILD_LIBRARY_TYPE=Shared "-DINSTALL_DIR=$prefix" "$@" \
    > "$build/configure.log" 2>&1
cxx=$(sed -n 's/^CMAKE_CXX_COMPILER:FILEPATH=//p' "$build/CMakeCache.txt")
[ -n "$cxx" ] || cxx=$(sed -n 's/^CMAKE_CXX_COMPILER:STRING=//p' "$build/CMakeCache.txt")
[ -x "$cxx" ] || { echo 'No configured C++ compiler' >&2; exit 1; }
case "$("$cxx" -dumpfullversion)" in 16.*) ;; *) echo 'Compiler must be GCC16' >&2; exit 1;; esac
if [ "$mode" = cross-full ]; then
    case "$("$cxx" -dumpmachine)" in aarch64*-netbsd*) ;; *) echo 'Expected AArch64 NetBSD compiler identity' >&2; exit 1;; esac
fi
cmake --build "$build" --parallel "$jobs" > "$build/build.log" 2>&1
DESTDIR="$stage" cmake --install "$build" > "$build/install.log" 2>&1
printf 'Prepared %s OCCT stage: %s\n' "$mode" "$stage"
