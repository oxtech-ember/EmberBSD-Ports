#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Check the actual upstream CMake files before and after the Ports patches.
set -eu
if [ "$#" -lt 4 ]; then
    echo "Usage: $0 UPSTREAM_SOURCE PATCHED_SOURCE UTHASH_SOURCE WORK_DIR [CMAKE_ARG ...]" >&2
    exit 2
fi
upstream=$1
patched=$2
uthash=$3
work=$4
shift 4
cmake=${CMAKE:-cmake}
for path in "$upstream/CMakeLists.txt" "$patched/CMakeLists.txt" "$uthash/src/uthash.h"; do
    [ -f "$path" ] || { echo "Missing input: $path" >&2; exit 2; }
done
[ ! -e "$work" ] || { echo "WORK_DIR must not exist: $work" >&2; exit 2; }
mkdir -p "$work/fixture"
work=$(cd "$work" && pwd)
upstream=$(cd "$upstream" && pwd)
patched=$(cd "$patched" && pwd)
uthash=$(cd "$uthash" && pwd)
# CMake's disabled-package switch gives a deterministic missing system package.
"$cmake" -S "$upstream" -B "$work/upstream-missing" "$@" \
    -DUSE_SYSTEM_UTHASH=ON -DCMAKE_DISABLE_FIND_PACKAGE_UTHash=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON > "$work/upstream-missing.log" 2>&1
grep -F "$upstream/uthash" "$work/upstream-missing/compile_commands.json" > /dev/null
if "$cmake" -S "$patched" -B "$work/patched-missing" "$@" \
    -DUSE_SYSTEM_UTHASH=ON -DCMAKE_DISABLE_FIND_PACKAGE_UTHash=ON \
    > "$work/patched-missing.log" 2>&1; then
    echo "FAIL: the patched project accepted a disabled system uthash" >&2
    exit 1
fi
grep -F 'REQUIRED' "$work/patched-missing.log" > /dev/null
grep -F 'UTHash' "$work/patched-missing.log" > /dev/null
# Import each real FindUTHash module and inspect its exported include contract.
cat > "$work/fixture/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.16)
project(UTHashIncludeContract NONE)
list(PREPEND CMAKE_MODULE_PATH "${MODULE_SOURCE}/cmake")
find_package(UTHash REQUIRED)
get_target_property(actual UTHash::UTHash INTERFACE_INCLUDE_DIRECTORIES)
if(EXPECT_VALID_INCLUDE)
    if(NOT actual STREQUAL UTHash_INCLUDE_DIR)
        message(FATAL_ERROR "UTHash imported '${actual}', expected '${UTHash_INCLUDE_DIR}'")
    endif()
else()
    if(actual STREQUAL UTHash_INCLUDE_DIR)
        message(FATAL_ERROR "The baseline no longer reproduces the include defect")
    endif()
endif()
CMAKE
"$cmake" -S "$work/fixture" -B "$work/upstream-include" \
    -DMODULE_SOURCE="$upstream" -DUTHash_INCLUDE_DIR="$uthash/src" \
    -DEXPECT_VALID_INCLUDE=OFF > "$work/upstream-include.log" 2>&1
"$cmake" -S "$work/fixture" -B "$work/patched-include" \
    -DMODULE_SOURCE="$patched" -DUTHash_INCLUDE_DIR="$uthash/src" \
    -DEXPECT_VALID_INCLUDE=ON > "$work/patched-include.log" 2>&1
printf '%s\n' 'PASS: upstream fallback reproduced; patched system requirement enforced.' \
    'PASS: upstream include defect reproduced; patched import uses the supplied directory.'
