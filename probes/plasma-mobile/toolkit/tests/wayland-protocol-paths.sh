#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Execute ECM's real Wayland protocol finder.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 ECM_SOURCE NEW_WORK" >&2; exit 2; }
source=$1 work=$2
: "${CMAKE:?Set native CMake}"
: "${PKG_CONFIG:?Set native pkg-config}"
case "$source:$work" in /*:/*) ;; *) exit 2;; esac
mkdir "$work"
mkdir -p "$work/project" "$work/pc" "$work/host/data/stable/xdg-shell" \
    "$work/root$work/host/data/stable/xdg-shell" "$work/empty-root"
printf '<protocol name="target"/>\n' > "$work/root$work/host/data/stable/xdg-shell/xdg-shell.xml"
printf '<protocol name="host"/>\n' > "$work/host/data/stable/xdg-shell/xdg-shell.xml"
cat > "$work/pc/wayland-protocols.pc" <<EOF
prefix=$work/host
pkgdatadir=\${prefix}/data
Name: Wayland Protocols
Description: Protocol data lookup regression
Version: 1.49
EOF
cat > "$work/project/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.30)
project(ProtocolDataLookup NONE)
list(PREPEND CMAKE_MODULE_PATH "${ECM_SOURCE}/find-modules")
find_package(WaylandProtocols 1.49 REQUIRED)
if(NOT WaylandProtocols_DATADIR STREQUAL EXPECTED_DIR)
    message(FATAL_ERROR "Unexpected protocol data directory: ${WaylandProtocols_DATADIR}")
endif()
CMAKE
export PKG_CONFIG_LIBDIR="$work/pc"
export PKG_CONFIG_PATH=
export PKG_CONFIG_SYSROOT_DIR=
"$CMAKE" -S "$work/project" -B "$work/cross" \
    -DECM_SOURCE="$source" -DPKG_CONFIG_EXECUTABLE="$PKG_CONFIG" \
    -DCMAKE_SYSTEM_NAME=NetBSD -DCMAKE_FIND_ROOT_PATH="$work/root" \
    -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
    -DEXPECTED_DIR="$work/root$work/host/data" > "$work/cross.log" 2>&1
"$CMAKE" -S "$work/project" -B "$work/native" \
    -DECM_SOURCE="$source" -DPKG_CONFIG_EXECUTABLE="$PKG_CONFIG" \
    -DEXPECTED_DIR="$work/host/data" > "$work/native.log" 2>&1
if "$CMAKE" -S "$work/project" -B "$work/missing" \
    -DECM_SOURCE="$source" -DPKG_CONFIG_EXECUTABLE="$PKG_CONFIG" \
    -DCMAKE_SYSTEM_NAME=NetBSD -DCMAKE_FIND_ROOT_PATH="$work/empty-root" \
    -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
    -DEXPECTED_DIR="$work/host/data" > "$work/missing.log" 2>&1; then
    echo 'Missing target protocols accepted via host data' >&2; exit 1
fi
grep -q 'Could NOT find WaylandProtocols' "$work/missing.log"
echo 'PASS: actual ECM finder selects target sysroot, preserves native lookup and rejects host fallback'
