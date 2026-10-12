#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 1 ] || { echo 'Usage: test.sh ABS_WORK' >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) echo 'Use an absolute work path.' >&2; exit 2 ;; esac
[ "$(uname -s)" = NetBSD ] || { echo 'Native EmberBSD/NetBSD required.' >&2; exit 2; }
build_as=${BUILD_AS_KIB:-}
if [ "${BUILD_AS_KIB+x}" = x ]; then
    case "$build_as" in ''|0|*[!0-9]*) echo 'BUILD_AS_KIB must be positive.' >&2; exit 2 ;; esac
    [ "$build_as" -gt 0 ] 2>/dev/null || { echo 'BUILD_AS_KIB must be positive.' >&2; exit 2; }
fi
# Optional user-selected soft limit; preserve the inherited hard limit.
if [ -n "$build_as" ]; then
    ulimit -S -v "$build_as" || { echo 'Could not set the requested address-space limit.' >&2; exit 2; }
    [ "$(ulimit -S -v)" = "$build_as" ] || {
        echo 'Requested address-space limit verification failed.' >&2; exit 2;
    }
fi
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
prefix=$work/install
[ -d "$prefix" ] && [ -d "$work/logs" ] || { echo 'The installed probe is missing.' >&2; exit 2; }
# Refuse a reused consumer build: cached package/compiler selections are evidence too.
[ ! -e "$work/test-build" ] || { echo 'Consumer build already exists; preserve it and use a new path.' >&2; exit 2; }
CXX=$(cat "$work/logs/cxx.txt")
[ -x "$CXX" ] || { echo 'The recorded C++ compiler is missing.' >&2; exit 2; }
EIGEN_PREFIX=$(cat "$work/logs/eigen-prefix.txt")
OPENCV_PREFIX=$(cat "$work/logs/opencv-prefix.txt")
PCL_PREFIX=$(cat "$work/logs/pcl-prefix.txt")
GTSAM_PREFIX=$(cat "$work/logs/gtsam-prefix.txt")
SQLITE_PREFIX=$(cat "$work/logs/sqlite-prefix.txt")
LD_LIBRARY_PATH=/usr/pkg/gcc16/lib:$prefix/lib:$OPENCV_PREFIX/lib:$PCL_PREFIX/lib:$GTSAM_PREFIX/lib:$SQLITE_PREFIX/lib:/usr/pkg/lib
export LD_LIBRARY_PATH
cmake -S "$recipe/tests" -B "$work/test-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DPROBE_PREFIX="$prefix" -DEIGEN_PREFIX="$EIGEN_PREFIX" \
    -DCMAKE_CXX_COMPILER="$CXX" -DOPENCV_PREFIX="$OPENCV_PREFIX" -DPCL_PREFIX="$PCL_PREFIX" \
    -DGTSAM_PREFIX="$GTSAM_PREFIX" -DSQLITE_PREFIX="$SQLITE_PREFIX" \
    -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
    > "$work/logs/consumer-configure.log" 2>&1 || { cat "$work/logs/consumer-configure.log" >&2; exit 1; }
cmake --build "$work/test-build" --parallel 1 > "$work/logs/consumer-build.log" 2>&1 || {
    cat "$work/logs/consumer-build.log" >&2; exit 1;
}
# The contract requires a new database path; remove any stale one.
rm -f "$work/test-build/map.db"
ctest --test-dir "$work/test-build" --output-on-failure --verbose > "$work/logs/consumer-test.log" 2>&1 || {
    cat "$work/logs/consumer-test.log" >&2; exit 1;
}
cat "$work/logs/consumer-test.log"
ldd "$work/test-build/rtabmap-contract" > "$work/logs/installed-linkage.txt"
grep -F "$prefix/lib/librtabmap_core.so" "$work/logs/installed-linkage.txt" >/dev/null || {
    echo 'The consumer did not load the installed rtabmap library.' >&2; exit 1;
}
if grep -E 'not found|libc[+][+]' "$work/logs/installed-linkage.txt" >/dev/null; then
    echo 'Missing dependency or mixed C++ runtime.' >&2; exit 1;
fi
expected_runtime=$("$CXX" -print-file-name=libstdc++.so)
[ -f "$expected_runtime" ] || { echo 'Compiler did not identify its C++ runtime.' >&2; exit 1; }
expected_runtime=$(realpath "$expected_runtime")
loaded_runtime=$(awk '/libstdc[+][+]/ {print $3}' "$work/logs/installed-linkage.txt")
[ -n "$loaded_runtime" ] && [ "$(printf '%s\n' "$loaded_runtime" | wc -l | tr -d ' ')" = 1 ] || {
    echo 'Expected exactly one loaded C++ runtime.' >&2; exit 1;
}
[ "$(realpath "$loaded_runtime")" = "$expected_runtime" ] || {
    echo 'Loaded C++ runtime differs from the recorded compiler runtime.' >&2; exit 1;
}
echo 'PASS installed library and coherent C++ runtime linkage'
