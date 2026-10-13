#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Build and install the real source, move its prefix, and link an installed consumer.
set -eu
[ "$#" -ge 3 ] || { echo "Usage: $0 UPSTREAM_SOURCE PATCHED_SOURCE NEW_WORK [CMAKE_ARG ...]" >&2; exit 2; }
upstream=$(CDPATH= cd -- "$1" && pwd)
patched=$(CDPATH= cd -- "$2" && pwd)
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
shift 3
cmake=${CMAKE:-cmake}
for source in "$upstream" "$patched"; do
    [ -f "$source/src/CMakeLists.txt" ] && [ -f "$source/src/encoding.c" ] || exit 2
done
mkdir "$work/consumer"
cat > "$work/consumer/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.16)
project(XCBImdkitRelocation C)
find_package(ECM REQUIRED NO_MODULE)
list(APPEND CMAKE_MODULE_PATH "${ECM_MODULE_PATH}")
find_package(XCB REQUIRED COMPONENTS XCB)
find_package(XCBImdkit CONFIG REQUIRED
    PATHS "${RELOCATED_PREFIX}/lib/cmake/XCBImdkit"
    NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH)
get_target_property(actual XCBImdkit::XCBImdkit INTERFACE_INCLUDE_DIRECTORIES)
file(WRITE "${CMAKE_BINARY_DIR}/include-dir.txt" "${actual}\n")
if(CHECK_RELOCATED_INCLUDE AND NOT actual STREQUAL "${RELOCATED_PREFIX}/include")
    message(FATAL_ERROR "Installed include path '${actual}' does not use the relocated prefix")
endif()
add_executable(consumer main.c)
target_link_libraries(consumer PRIVATE XCBImdkit::XCBImdkit)
CMAKE
cat > "$work/consumer/main.c" <<'C'
#include <xcb-imdkit/encoding.h>
#include <xcb-imdkit/imclient.h>

int
main(void)
{
    xcb_compound_text_init();
    return 0;
}
C
for variant in upstream patched; do
    case "$variant" in upstream) source=$upstream ;; patched) source=$patched ;; esac
    prefix=$work/absent-$variant
    [ ! -e "$prefix" ] || exit 1
    "$cmake" -S "$source" -B "$work/build-$variant" "$@" \
        -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_INCLUDEDIR=include \
        -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON > "$work/configure-$variant.log" 2>&1
    "$cmake" --build "$work/build-$variant" --parallel "${BUILD_JOBS:-2}" > "$work/build-$variant.log" 2>&1
    DESTDIR="$work/stage-$variant" "$cmake" --install "$work/build-$variant" > "$work/install-$variant.log" 2>&1
    mv "$work/stage-$variant$prefix" "$work/relocated-$variant"
    [ ! -e "$prefix" ] || exit 1
    case "$variant" in
        upstream)
            if "$cmake" -S "$work/consumer" -B "$work/consumer-upstream" "$@" \
                -DRELOCATED_PREFIX="$work/relocated-upstream" -DCHECK_RELOCATED_INCLUDE=OFF \
                > "$work/consumer-upstream.log" 2>&1; then
                echo 'FAIL: the baseline no longer reproduces the installed include-path defect' >&2; exit 1
            fi
            grep -F 'includes non-existent path' "$work/consumer-upstream.log" >/dev/null
            grep -F "$prefix/include" "$work/consumer-upstream.log" >/dev/null
            ;;
        patched)
            "$cmake" -S "$work/consumer" -B "$work/consumer-patched" "$@" \
                -DRELOCATED_PREFIX="$work/relocated-patched" -DCHECK_RELOCATED_INCLUDE=ON \
                -DCMAKE_EXPORT_COMPILE_COMMANDS=ON > "$work/consumer-patched.log" 2>&1
            "$cmake" --build "$work/consumer-patched" --parallel "${BUILD_JOBS:-2}" > "$work/consumer-build.log" 2>&1
            ;;
    esac
done
printf '%s\n' 'PASS: actual upstream install reproduces the relocation defect.' \
    'PASS: patched install exports the relocated include path and links its C API consumer.' \
    'Target execution and an input session are separate acceptance checks.'
