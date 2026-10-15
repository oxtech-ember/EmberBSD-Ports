#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Installed shared ONNX Runtime CPU provider.
set -eu
umask 022
[ "$#" = 5 ] || { echo 'Usage: build-runtime.sh cross|native GCC_PREFIX SYSROOT ARCHIVES NEW_OUTPUT' >&2; exit 2; }
mode=$1 compiler=$2 sysroot=$3 cache=$4 out=$5
case "$mode" in cross|native) ;; *) exit 2;; esac
for path in "$compiler" "$sysroot" "$cache" "$out"; do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple absolute paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Preserve the existing output.' >&2; exit 2; }
jobs=${JOBS:-2}
case "$jobs" in ''|0|*[!0-9]*) exit 2;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || exit 2
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
ports=$(CDPATH= cd "$recipe/../.." && pwd -P)
package=$ports/pkgsrc/local-ai/onnxruntime
sh "$recipe/fetch.sh" "$cache"
mkdir -p "$out/source" "$out/logs" "$out/dependencies"
tar -xf "$cache/onnxruntime-1.31.0.tar.gz" --strip-components=1 -C "$out/source"
sha256sum "$cache/onnxruntime-1.31.0.tar.gz" "$package/features.cmake" "$0" "$package"/patches/patch-* > "$out/inputs.sha256"
for patch in "$package"/patches/patch-*; do
    patch --fuzz=0 -d "$out/source" -p1 < "$patch" >> "$out/logs/patch.log" 2>&1
done
while read -r name hash url; do
    mirror=$out/dependencies/${url#https://}
    mkdir -p "$(dirname "$mirror")"
    cp "$cache/$name" "$mirror"
done < "$recipe/dependencies.tsv"
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
if [ "$mode" = cross ]; then
    for language in gcc g++; do
        [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpfullversion)" = 16.2.0 ]
        [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpmachine)" = aarch64--netbsd ]
    done
    crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
    runtime=$sysroot/usr/pkg/gcc16/lib
    headers=$sysroot/usr/pkg/gcc16/include/c++
    [ -f "$crt/crtbeginS.o" ] && [ -f "$runtime/libstdc++.so.7" ]
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
    set -- -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_INSTALL_PREFIX=/usr/pkg \
        -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib'
else
    [ "$(gcc -dumpfullversion)" = 16.2.0 ]
    [ "$(g++ -dumpfullversion)" = 16.2.0 ]
    set -- -DCMAKE_C_COMPILER="$(command -v gcc)" -DCMAKE_CXX_COMPILER="$(command -v g++)" \
        -DCMAKE_INSTALL_PREFIX="$out/install" -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
        "-DCMAKE_INSTALL_RPATH=$out/install/lib;/usr/local/lib64"
fi
[ -f "$sysroot/usr/pkg/share/eigen3/cmake/Eigen3Config.cmake" ]
if [ -n "${SSL_CERT_FILE:-}" ]; then
    set -- "$@" "-DCMAKE_TLS_CAINFO=$SSL_CERT_FILE"
fi
cmake -S "$out/source/cmake" -B "$out/build" -G Ninja -C "$package/features.cmake" \
    "$@" -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DEigen3_DIR="$sysroot/usr/pkg/share/eigen3/cmake" \
    -Donnxruntime_CMAKE_DEPS_MIRROR_DIR="$out/dependencies" \
    -DPatch_EXECUTABLE="$(command -v patch)" -DPython_EXECUTABLE="$(command -v python3)" \
    -DCMAKE_TLS_VERIFY=ON -DFLATBUFFERS_BUILD_FLATC=OFF > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --target onnxruntime onnxruntime_providers_shared --parallel "$jobs" > "$out/logs/build.log" 2>&1
# Install only the runtime's own generated rules. Private static build inputs
# must not install competing public dependency SDKs into the common prefix.
if [ "$mode" = cross ]; then
    DESTDIR="$out/stage" cmake -DCMAKE_INSTALL_LOCAL_ONLY=ON -P "$out/build/cmake_install.cmake" > "$out/logs/install.log" 2>&1
    prefix=$out/stage/usr/pkg
else
    cmake -DCMAKE_INSTALL_LOCAL_ONLY=ON -P "$out/build/cmake_install.cmake" > "$out/logs/install.log" 2>&1
    prefix=$out/install
fi
sh "$package/files/install-licenses.sh" "$out/source" "$out/build" "$prefix" "$package"
(cd "$prefix" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/files.txt"
sed '/^@comment/d' "$package/PLIST" | LC_ALL=C sort > "$out/expected-files.txt"
cmp "$out/expected-files.txt" "$out/files.txt"
echo "Installed ONNX Runtime 1.31.0 ($mode): $prefix"
