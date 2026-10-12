#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), CMake imported-target cross-path regression.
set -eu
[ "$#" = 2 ] || { echo 'Usage: archive-pkgconfig.sh PREPARED_PKGSRC NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set cross MAKECONF}" "${CMAKE:?Set native CMake}" "${PKG_CONFIG:?Set native pkg-config}"
recipe=$1/archivers/kf6-karchive
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
sysroot=$("$BMAKE" -C "$recipe" -V '${CROSS_DESTDIR}')
prefix=$("$BMAKE" -C "$recipe" -V '${PREFIX}')
selected=$("$BMAKE" -C "$recipe" -V '${CONFIGURE_ENV:MPKG_CONFIG_SYSROOT_DIR=*}')
[ "$selected" = "PKG_CONFIG_SYSROOT_DIR=$sysroot" ]
[ -z "$("$BMAKE" -C "$recipe" USE_CROSS_COMPILE=no -V '${CONFIGURE_ENV:MPKG_CONFIG_SYSROOT_DIR=*}')" ]
mkdir "$work/source"
cat > "$work/source/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.25)
project(ArchiveImportedPath C)
find_package(PkgConfig REQUIRED)
pkg_check_modules(LibZstd REQUIRED IMPORTED_TARGET libzstd)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/consumer.c" "#include <zstd.h>\nint main(void) { return ZSTD_versionNumber() == 0; }\n")
add_executable(consumer "${CMAKE_CURRENT_BINARY_DIR}/consumer.c")
target_link_libraries(consumer PRIVATE PkgConfig::LibZstd)
get_target_property(paths PkgConfig::LibZstd INTERFACE_INCLUDE_DIRECTORIES)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/includes.txt" "${paths}\n")
CMAKE
export PKG_CONFIG
PKG_CONFIG_LIBDIR=$sysroot$prefix/lib/pkgconfig; export PKG_CONFIG_LIBDIR
PKG_CONFIG_PATH=; export PKG_CONFIG_PATH
# Reproduce the original host-time validation failure with the real target .pc.
if [ ! -d "$prefix/include" ]; then
    if env PKG_CONFIG_SYSROOT_DIR= "$CMAKE" -S "$work/source" -B "$work/old" > "$work/old.log" 2>&1; then
        echo 'The original unrooted imported target unexpectedly configured' >&2; exit 1
    fi
    grep -q 'non-existent path' "$work/old.log"
else
    echo 'SKIP: an existing native target prefix hides the original failure'
fi
env "$selected" "$CMAKE" -S "$work/source" -B "$work/cross" > "$work/cross.log" 2>&1
grep -Fq "$sysroot$prefix/include" "$work/cross/includes.txt"
echo 'PASS: actual target Zstd metadata configures with the recipe sysroot; native selection is unchanged'
