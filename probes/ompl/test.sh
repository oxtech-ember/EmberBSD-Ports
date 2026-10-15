#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 1 ] || { echo 'Usage: test.sh ABS_WORK' >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) exit 2 ;; esac
case "$work" in *[!a-zA-Z0-9_./-]*) exit 2 ;; esac
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
prefix=$work/install
eigen=$(cat "$work/eigen-prefix.txt")
boost=$(cat "$work/boost-prefix.txt")
case "$(uname -s)" in
    NetBSD)
        CC=${CC:-/usr/pkg/gcc16/bin/gcc}
        CXX=${CXX:-/usr/pkg/gcc16/bin/g++}
        export CC CXX
        [ "$("$CC" -dumpfullversion)" = 16.2.0 ]
        [ "$("$CXX" -dumpfullversion)" = 16.2.0 ]
        if [ "${BUILD_AS_KIB+x}" = x ]; then
            case "$BUILD_AS_KIB" in ''|*[!0-9]*) exit 2 ;; esac
            [ "$BUILD_AS_KIB" -gt 0 ] 2>/dev/null || exit 2
            ulimit -S -v "$BUILD_AS_KIB"
        fi ;;
    Darwin) echo 'Host-only macOS check; this does not validate NetBSD.' ;;
    *) echo 'Unsupported test host.' >&2; exit 2 ;;
esac
cmake=${CMAKE:-cmake}
"$cmake" -S "$recipe/tests" -B "$work/test-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DPROBE_PREFIX="$prefix" \
    -DEIGEN_PREFIX="$eigen" -DBOOST_PREFIX="$boost" \
    -DCMAKE_BUILD_RPATH="$prefix/lib;$boost/lib"
"$cmake" --build "$work/test-build" --parallel 1
status=0
"${CTEST:-ctest}" --test-dir "$work/test-build" --verbose > "$work/logs/contracts.txt" 2>&1 || status=$?
cat "$work/logs/contracts.txt"
[ "$status" = 0 ] || exit "$status"
if [ "$(uname -s)" = NetBSD ]; then
    ldd "$work/test-build/ompl-contract" > "$work/logs/installed-linkage.txt"
    for library in "$prefix/lib/libompl.so" "$boost/lib/libboost_serialization.so.1.92.0" \
        /usr/pkg/gcc16/lib/libstdc++.so.7 /usr/pkg/gcc16/lib/libgcc_s.so.1; do
        grep -F "$library" "$work/logs/installed-linkage.txt" >/dev/null
    done
    if grep -E 'not found|libpython|libflann|libspot|libyaml|libvamp' "$work/logs/installed-linkage.txt"; then exit 1; fi
    readelf -h "$prefix/lib/libompl.so" > "$work/logs/elf-header.txt"
    grep 'AArch64' "$work/logs/elf-header.txt" >/dev/null
else
    otool -L "$work/test-build/ompl-contract" > "$work/logs/installed-linkage.txt"
fi
echo 'Installed OMPL bounded planner and independent geometry checks passed.'
