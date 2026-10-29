#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Installed common-prefix mapping contracts.
set -eu
[ "$#" = 2 ] || { echo 'Usage: test.sh ABS_WORK PATCHED_OPENCV_SOURCE' >&2; exit 2; }
work=$1 opencv_source=$2
for path do
    case "$path" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ "$(uname -s):$(uname -p)" = NetBSD:aarch64 ] || { echo 'Native AArch64 EmberBSD required.' >&2; exit 2; }
[ -z "${LD_LIBRARY_PATH:-}" ] && [ -z "${LD_PRELOAD:-}" ] || {
    echo 'Use an ordinary loader environment.' >&2; exit 2;
}
[ -f "$opencv_source/modules/core/include/opencv2/core/utils/plugin_loader.private.hpp" ] || {
    echo 'The exact patched OpenCV source is required.' >&2; exit 2;
}
build_as=${BUILD_AS_KIB:-}
if [ "${BUILD_AS_KIB+x}" = x ]; then
    case "$build_as" in ''|*[!0-9]*) build_as=0;; esac
    [ "$build_as" -gt 0 ] 2>/dev/null || { echo 'BUILD_AS_KIB must be positive.' >&2; exit 2; }
    ulimit -S -v "$build_as"
    [ "$(ulimit -S -v)" = "$build_as" ] || exit 2
fi
probe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
prefix=$work/install
[ -d "$prefix" ] && [ -d "$work/logs" ] || exit 2
[ ! -e "$work/test-build" ] && [ ! -L "$work/test-build" ] || {
    echo 'Consumer build already exists; preserve it and use a new path.' >&2; exit 2;
}
CC=$(cat "$work/logs/cc.txt")
CXX=$(cat "$work/logs/cxx.txt")
common=$(cat "$work/logs/common-prefix.txt")
[ -d "$common" ] || exit 2
for compiler in "$CC" "$CXX"; do
    [ -x "$compiler" ] && [ "$("$compiler" -dumpversion)" = 23.1.4 ] || exit 2
done
printf '%s\n' "$opencv_source" > "$work/logs/opencv-source.txt"
run() {
    stage=$1; shift
    status=0
    "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$work/logs/$stage.status"
    [ "$status" = 0 ] || { cat "$work/logs/$stage.log" >&2; exit "$status"; }
}
run consumer-configure cmake -S "$probe/tests" -B "$work/test-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DPROBE_PREFIX="$prefix" -DCMAKE_PREFIX_PATH="$prefix;$common" \
    -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" \
    -DEIGEN_PREFIX="$common" -DOPENCV_PREFIX="$common" -DPCL_PREFIX="$common" \
    -DGTSAM_PREFIX="$common" -DSQLITE_PREFIX="$common" -DLZ4_PREFIX="$common" \
    -Dlz4_DIR="$common/lib/cmake/lz4" -DOPENCV_SOURCE="$opencv_source" \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;$common/lib;$common/llvm/lib" \
    -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF
run consumer-build cmake --build "$work/test-build" --parallel 1
run consumer-test ctest --test-dir "$work/test-build" --no-tests=error --output-on-failure --verbose
cat "$work/logs/consumer-test.log"
ldd "$work/test-build/rtabmap-contract" > "$work/logs/installed-linkage.txt"
grep -F "$prefix/lib/librtabmap_core.so" "$work/logs/installed-linkage.txt" >/dev/null
if grep -E 'not found|libstdc[+][+]|libgcc_s' "$work/logs/installed-linkage.txt" >/dev/null; then exit 1; fi
expected=$common/llvm/lib/libc++.so.1
[ -f "$expected" ] || exit 1
loaded=$(awk '/libc[+][+][.]so/ {print $3}' "$work/logs/installed-linkage.txt")
[ -n "$loaded" ] && [ "$(printf '%s\n' "$loaded" | wc -l | tr -d ' ')" = 1 ] || exit 1
[ "$(realpath "$loaded")" = "$(realpath "$expected")" ] || exit 1
echo 'PASS installed mapping/dependency contracts and coherent Clang libc++ runtime'
