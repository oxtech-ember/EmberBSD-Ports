#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Native installed PCL consumer checks.
set -eu
[ "$#" = 1 ] || { echo 'Usage: test.sh ABS_WORK' >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) echo 'Use an absolute work path.' >&2; exit 2;; esac
case "$work" in *[!A-Za-z0-9_./-]*) echo 'Use a simple work path.' >&2; exit 2;; esac
[ "$(uname -s)" = NetBSD ] || { echo 'Native EmberBSD/NetBSD required.' >&2; exit 2; }
[ -z "${LD_LIBRARY_PATH:-}" ] && [ -z "${LD_PRELOAD:-}" ] || {
    echo 'Run with an ordinary loader environment.' >&2; exit 2;
}
build_as=${BUILD_AS_KIB:-}
if [ "${BUILD_AS_KIB+x}" = x ]; then
    case "$build_as" in ''|*[!0-9]*) build_as=0;; esac
    [ "$build_as" -gt 0 ] 2>/dev/null || { echo 'BUILD_AS_KIB must be positive.' >&2; exit 2; }
fi
if [ -n "$build_as" ]; then
    ulimit -S -v "$build_as" || { echo 'Could not set the requested address-space limit.' >&2; exit 2; }
    [ "$(ulimit -S -v)" = "$build_as" ] || { echo 'Address-space limit verification failed.' >&2; exit 2; }
fi
probe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
prefix=$work/install
[ -d "$prefix" ] && [ -d "$work/logs" ] || { echo 'The installed PCL probe is missing.' >&2; exit 2; }
[ ! -e "$work/test-build" ] && [ ! -L "$work/test-build" ] || {
    echo 'Consumer build already exists; preserve it and use a new path.' >&2; exit 2;
}
CC=$(cat "$work/logs/cc.txt")
CXX=$(cat "$work/logs/cxx.txt")
common=$(cat "$work/logs/common-prefix.txt")
[ -d "$common" ] && [ -x "$CC" ] && [ -x "$CXX" ] || { echo 'Recorded compiler/dependencies missing.' >&2; exit 2; }
[ "$("$CC" -dumpfullversion)" = 16.2.0 ] && [ "$("$CXX" -dumpfullversion)" = 16.2.0 ] || {
    echo 'Recorded GCC 16.2.0 compiler required.' >&2; exit 2;
}
run() {
    stage=$1
    shift
    status=0
    "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$work/logs/$stage.status"
    if [ "$status" -ne 0 ]; then
        cat "$work/logs/$stage.log" >&2
        exit "$status"
    fi
}
run consumer-configure cmake -S "$probe/tests" -B "$work/test-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DPROBE_PREFIX="$prefix" \
    -DFLANN_PREFIX="$common" -DEIGEN_PREFIX="$common" -DBOOST_PREFIX="$common" \
    -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;$common/lib;$common/gcc16/lib" \
    -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF
run consumer-build cmake --build "$work/test-build" --parallel 1
run consumer-test ctest --test-dir "$work/test-build" --no-tests=error --output-on-failure --verbose
cat "$work/logs/consumer-test.log"
for binary in pcl-contract lz4-zero-buffers boost-iostreams-contract; do
    ldd "$work/test-build/$binary" > "$work/logs/$binary-linkage.txt"
    if grep -E 'not found|libc[+][+]' "$work/logs/$binary-linkage.txt" >/dev/null; then
        echo "Missing dependency or mixed C++ runtime in $binary." >&2; exit 1;
    fi
done
cp "$work/logs/pcl-contract-linkage.txt" "$work/logs/installed-linkage.txt"
for library in libpcl_common.so libpcl_filters.so libpcl_registration.so; do
    grep -F "$prefix/lib/$library" "$work/logs/installed-linkage.txt" >/dev/null || {
        echo "The consumer did not load the installed $library." >&2; exit 1;
    }
done
# FLANN's C++ API uses templates. Its installed CMake target is checked by the
# consumer configuration; the empty wrapper DSO need not become DT_NEEDED.
grep -F "$common/lib/liblz4.so" "$work/logs/lz4-zero-buffers-linkage.txt" >/dev/null
for library in libboost_iostreams.so.1.92.0 libboost_random.so.1.92.0; do
    grep -F "$common/lib/$library" "$work/logs/boost-iostreams-contract-linkage.txt" >/dev/null
done
for binary in pcl-contract boost-iostreams-contract; do
    for library in libstdc++.so libgcc_s.so.1; do
        expected=$("$CXX" -print-file-name="$library")
        [ -f "$expected" ] || { echo "Compiler runtime missing: $library" >&2; exit 1; }
        case "$library" in libstdc++.so) pattern='libstdc[+][+]' ;; *) pattern='libgcc_s' ;; esac
        loaded=$(awk -v pattern="$pattern" '$0 ~ pattern {print $3}' "$work/logs/$binary-linkage.txt")
        [ -n "$loaded" ] && [ "$(printf '%s\n' "$loaded" | wc -l | tr -d ' ')" = 1 ] || {
            echo "Expected one loaded $library in $binary." >&2; exit 1;
        }
        [ "$(realpath "$loaded")" = "$(realpath "$expected")" ] || {
            echo "Loaded $library differs from the recorded compiler runtime." >&2; exit 1;
        }
    done
done
echo 'PASS installed PCL/dependency consumers and common GCC16 runtime linkage'
