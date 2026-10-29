#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Check Darwin's default zlib and explicitly selected provider.
set -eu
[ "$#" = 4 ] || { echo 'Usage: zlib-provider.sh QTBASE_SOURCE CMAKE PATCH ZLIB_ROOT' >&2; exit 2; }
source=$1 cmake=$2 patch=$3 root=$4
case "$(uname -s)" in Darwin) ;; *) echo 'Darwin required' >&2; exit 2;; esac
cross=$(CDPATH= cd -- "$(dirname -- "$0")/../cross" && pwd)
fix=$cross/../../../../pkgsrc/x11/qt6-qtbase/patches/patch-cmake_FindWrapSystemZLIB.cmake
tmp=$(mktemp -d "${TMPDIR:-/tmp}/ember-qt-zlib-test.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
mkdir -p "$tmp/src/cmake"
cp "$source/cmake/FindWrapSystemZLIB.cmake" "$tmp/src/cmake/"
"$patch" -d "$tmp/src" -p0 -F0 -i "$fix" >/dev/null
cat > "$tmp/src/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.20)
project(zlib_provider C)
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
find_package(WrapSystemZLIB REQUIRED)
get_target_property(actual WrapSystemZLIB::WrapSystemZLIB INTERFACE_LINK_LIBRARIES)
if(NOT "${actual}" STREQUAL "${expected}")
  message(FATAL_ERROR "Unexpected zlib target: ${actual}")
endif()
if(expected STREQUAL "ZLIB::ZLIB")
  get_target_property(location ZLIB::ZLIB IMPORTED_LOCATION_RELEASE)
  if(NOT location MATCHES "^${expected_root}/")
    message(FATAL_ERROR "Unexpected zlib location: ${location}")
  endif()
endif()
CMAKE
env -u ZLIB_ROOT "$cmake" -S "$tmp/src" -B "$tmp/default" -Dexpected=-lz >/dev/null
env -u ZLIB_ROOT "$cmake" -S "$tmp/src" -B "$tmp/root" -Dexpected=ZLIB::ZLIB -Dexpected_root="$root" -DZLIB_ROOT="$root" >/dev/null
env -u ZLIB_ROOT "$cmake" -S "$tmp/src" -B "$tmp/static" -Dexpected=ZLIB::ZLIB -Dexpected_root="$root" -DZLIB_ROOT="$root" -DZLIB_USE_STATIC_LIBS=ON >/dev/null
ZLIB_ROOT="$root" "$cmake" -S "$tmp/src" -B "$tmp/env" -Dexpected=ZLIB::ZLIB -Dexpected_root="$root" >/dev/null
echo 'Darwin zlib provider selection PASS'
