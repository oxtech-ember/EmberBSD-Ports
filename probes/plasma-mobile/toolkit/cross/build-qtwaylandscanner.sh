#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Bootstrap one missing native Qt tool.
set -eu
[ "$#" = 5 ] || { echo "Usage: $0 DISTFILES HOST_QT SOURCE OBJECTS PREFIX" >&2; exit 2; }
dist=$1 host=$2 source=$3 objects=$4 prefix=$5
jobs=${JOBS:-4}
case "$jobs" in ''|*[!0-9]*|0) echo 'JOBS must be positive.' >&2; exit 2 ;; esac
case "${RESUME:-0}" in 0|1) ;; *) echo 'RESUME must be 0 or 1.' >&2; exit 2 ;; esac
for path do
    case "$path" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
    case "$path/" in */../*) echo 'Parent path components are not allowed.' >&2; exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) echo 'Use paths without shell metacharacters.' >&2; exit 2 ;; esac
done
source=${source%/} objects=${objects%/} prefix=${prefix%/}
case "$source/" in "$objects/"*|"$prefix/"*) echo 'Source and output paths overlap.' >&2; exit 2 ;; esac
case "$objects/" in "$source/"*) echo 'Source and object paths overlap.' >&2; exit 2 ;; esac
case "$prefix/" in "$source/"*|"$objects/") echo 'Source or output paths overlap.' >&2; exit 2 ;; esac
for path in "$source" "$objects" "$prefix"; do
    [ ! -L "$path" ] || { echo 'Source and output paths must not be symlinks.' >&2; exit 2; }
done
: "${WAYLAND_SCANNER:?Select the native Wayland 1.26 scanner}"
cmake=$(command -v "${CMAKE:-cmake}")
ninja=$(command -v "${NINJA:-ninja}")
cc=$(command -v "${HOST_CC:-cc}")
cxx=$(command -v "${HOST_CXX:-c++}")
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
scanner_patch=$root/../../../pkgsrc/x11/qt6-qtbase/patches/patch-src_tools_qtwaylandscanner_qtwaylandscanner.cpp
archive=qtbase-everywhere-src-6.12.0.tar.xz
expected=$(awk -F '\t' -v name="$archive" '$2 == name { print $3 }' "$root/sources.tsv")
[ -n "$expected" ] || { echo "Missing Qt archive hash in sources.tsv." >&2; exit 2; }
[ "$(shasum -a 256 "$dist/$archive" | awk '{print $1}')" = "$expected" ] || {
    echo "Qt archive checksum mismatch." >&2; exit 2;
}
[ "$("$host/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
[ "$("$WAYLAND_SCANNER" --version 2>&1)" = 'wayland-scanner 1.26.0' ]
for module in Core BuildInternals; do
    [ -f "$host/lib/cmake/Qt6$module/Qt6${module}Config.cmake" ]
done
inputs=$(printf '%s\n' "$expected" "$host" "$objects" "$prefix" "$WAYLAND_SCANNER"; \
    shasum -a 256 "$0" "$scanner_patch" "$cmake" "$ninja" "$cc" "$cxx" "$host/bin/qmake" "$WAYLAND_SCANNER"; \
    "$cmake" --version; "$cc" --version; "$cxx" --version)
if [ "${RESUME:-0}" = 1 ]; then
    [ -f "$source/inputs.txt" ] || { echo "Cannot resume missing source inputs." >&2; exit 2; }
    [ "$(cat "$source/inputs.txt")" = "$inputs" ] || { echo 'Bootstrap inputs changed.' >&2; exit 2; }
    (cd "$source" && shasum -a 256 -c sources.sha256)
else
    [ ! -e "$source" ] && [ ! -e "$prefix" ] && [ ! -e "$objects/CMakeCache.txt" ] || {
        echo 'Use new source/prefix and an unconfigured object directory, or RESUME=1.' >&2; exit 2;
    }
    mkdir -p "$source"
    printf '%s\n' "$inputs" > "$source/inputs.txt"
    tar -xf "$dist/$archive" -C "$source" --strip-components=1 \
        qtbase-everywhere-src-6.12.0/src/tools/qtwaylandscanner
    tar -xf "$dist/$archive" -C "$source" --strip-components=1 \
        qtbase-everywhere-src-6.12.0/LICENSES
    patch -d "$source" -p0 -F0 -i "$scanner_patch"
    cat > "$source/.cmake.conf" <<'CMAKE'
set(QT_REPO_MODULE_VERSION "6.12.0")
CMAKE
    cat > "$source/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.25)
include(.cmake.conf)
project(QtWaylandScannerBootstrap VERSION ${QT_REPO_MODULE_VERSION} LANGUAGES C CXX)
find_package(Qt6 6.12.0 EXACT REQUIRED COMPONENTS BuildInternals Core)
qt_internal_project_setup()
qt_build_repo()
file(WRITE "${CMAKE_BINARY_DIR}/installed-scanner-path.txt"
    "${CMAKE_INSTALL_PREFIX}/${INSTALL_LIBEXECDIR}/qtwaylandscanner\n")
CMAKE
    printf '%s\n' 'add_subdirectory(tools/qtwaylandscanner)' > "$source/src/CMakeLists.txt"
    (cd "$source" && shasum -a 256 .cmake.conf CMakeLists.txt src/CMakeLists.txt \
        src/tools/qtwaylandscanner/* > sources.sha256)
fi
mkdir -p "$objects"
"$cmake" -S "$source" -B "$objects" -G Ninja \
    -DCMAKE_C_COMPILER:FILEPATH="$cc" -DCMAKE_CXX_COMPILER:FILEPATH="$cxx" \
    -DCMAKE_MAKE_PROGRAM:FILEPATH="$ninja" -DCMAKE_PREFIX_PATH:PATH="$host" \
    -DCMAKE_INSTALL_PREFIX:PATH="$prefix" -DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON \
    -DQT_BUILD_TESTS:BOOL=OFF -DQT_BUILD_EXAMPLES:BOOL=OFF \
    -DWaylandScanner_EXECUTABLE:FILEPATH="$WAYLAND_SCANNER" > "$objects/configure.log" 2>&1
"$cmake" --build "$objects" --target qtwaylandscanner -j "$jobs" > "$objects/build.log" 2>&1
"$cmake" --install "$objects" > "$objects/install.log" 2>&1
scanner=$(cat "$objects/installed-scanner-path.txt")
[ -x "$scanner" ]
[ -f "$prefix/lib/cmake/Qt6WaylandScannerTools/Qt6WaylandScannerToolsConfig.cmake" ]
shasum -a 256 "$scanner" > "$objects/tool.sha256"
printf 'Built native Qt 6.12 scanner: %s\n' "$scanner"
