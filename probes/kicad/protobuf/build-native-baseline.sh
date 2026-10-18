#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors. Prepared with AI assistance.
# Build a native causal control. This does not create a target dependency stage.
set -eu
probe=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${PROTOBUF_WORK:?Set the prepared private build directory}"
: "${PKGSRC_BASE:?Set the pinned pkgsrc source root}"
: "${NATIVE_CC:?Set native GCC 16.2.0}"
: "${NATIVE_CXX:?Set native GCC 16.2.0}"
: "${NATIVE_ZLIB_PREFIX:?Set the common native zlib 1.3.2 prefix}"
case "$PROTOBUF_WORK" in /*) ;; *) exit 2;; esac
[ "$("$NATIVE_CC" -dumpfullversion)" = 16.2.0 ]
[ "$("$NATIVE_CXX" -dumpfullversion)" = 16.2.0 ]
jobs=${JOBS:-1}
case "$jobs" in ''|*[!0-9]*|0) exit 2;; esac
control=$PROTOBUF_WORK/causal-control
[ ! -e "$control" ] || { echo "Use a new causal-control directory" >&2; exit 2; }
(cd "$PROTOBUF_WORK/downloads" && sha256sum -c "$probe/sources.sha256")
mkdir -p "$control/source" "$control/upb-project" "$control/protoc-project"
tar -xf "$PROTOBUF_WORK/downloads/protobuf-36.2.tar.gz" \
    -C "$control/source" --strip-components=1
for name in patch-src_file__lists.cmake patch-src_google_protobuf_io_zero_copy_stream_impl.cc; do
    patchfile=$PKGSRC_BASE/devel/protobuf/patches/$name
    patch --fuzz=0 -d "$control/source" -p0 < "$patchfile"
    sha256sum "$patchfile" >> "$control/source-patches.sha256"
done
cat > "$control/upb-project/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.24)
project(upb_causal_control LANGUAGES C CXX)
set(protobuf_BUILD_LIBPROTOBUF ON CACHE BOOL "" FORCE)
set(protobuf_BUILD_PROTOC_BINARIES OFF CACHE BOOL "" FORCE)
set(protobuf_BUILD_LIBUPB ON CACHE BOOL "" FORCE)
set(protobuf_LOCAL_DEPENDENCIES_ONLY ON CACHE BOOL "" FORCE)
set(protobuf_INSTALL OFF CACHE BOOL "" FORCE)
add_subdirectory("${CONTROL_SOURCE}" protobuf)
add_executable(upb-baseline "${CONTRACT_SOURCE}")
target_link_libraries(upb-baseline PRIVATE protobuf::libupb)
target_compile_options(upb-baseline PRIVATE -Wall -Wextra -Wpedantic)
CMAKE
cmake -S "$control/upb-project" -B "$control/upb-build" -G Ninja \
    -DCONTROL_SOURCE="$control/source" -DCONTRACT_SOURCE="$probe/upb-oom-contract.c" \
    -DCMAKE_C_COMPILER="$NATIVE_CC" -DCMAKE_CXX_COMPILER="$NATIVE_CXX" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS=-g -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_PREFIX_PATH="$PROTOBUF_WORK/native" \
    -Dprotobuf_BUILD_SHARED_LIBS=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DZLIB_INCLUDE_DIR="$NATIVE_ZLIB_PREFIX/include" \
    -DZLIB_LIBRARY_RELEASE="$NATIVE_ZLIB_PREFIX/lib/libz.so"
cmake --build "$control/upb-build" --target upb-baseline -j "$jobs"
# The CLI differs only in main.cc. Link the control to the same installed
# compiler library and shared dependencies as the patched executable.
cat > "$control/protoc-project/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.24)
project(protoc_causal_control LANGUAGES C CXX)
find_package(Protobuf 36.2.0 EXACT CONFIG REQUIRED)
add_executable(protoc-baseline "${CONTROL_SOURCE}/src/google/protobuf/compiler/main.cc")
target_include_directories(protoc-baseline PRIVATE "${CONTROL_SOURCE}/src")
target_compile_features(protoc-baseline PRIVATE cxx_std_17)
target_link_libraries(protoc-baseline PRIVATE protobuf::libprotoc protobuf::libprotobuf)
CMAKE
cmake -S "$control/protoc-project" -B "$control/protoc-build" -G Ninja \
    -DCONTROL_SOURCE="$control/source" \
    -DCMAKE_C_COMPILER="$NATIVE_CC" -DCMAKE_CXX_COMPILER="$NATIVE_CXX" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS=-g -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_PREFIX_PATH="$PROTOBUF_WORK/native" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_INSTALL_RPATH="$PROTOBUF_WORK/native/lib;$NATIVE_ZLIB_PREFIX/lib" \
    -DZLIB_INCLUDE_DIR="$NATIVE_ZLIB_PREFIX/include" \
    -DZLIB_LIBRARY_RELEASE="$NATIVE_ZLIB_PREFIX/lib/libz.so"
cmake --build "$control/protoc-build" -j "$jobs"
sha256sum "$control/upb-build/upb-baseline" "$control/protoc-build/protoc-baseline" \
    > "$control/executables.sha256"
