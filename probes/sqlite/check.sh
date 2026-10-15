#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Check the selected installed SQLite shared library.
set -eu
umask 077
usage() {
    echo 'Usage: check.sh --native SQLITE_PREFIX NEW_OUTPUT' >&2
    echo '       check.sh --cross GCC_PREFIX SYSROOT STAGE_PREFIX NEW_OUTPUT' >&2
    exit 2
}
mode=${1:-}
[ "$#" -gt 0 ] || usage
shift
case "$mode" in
    --native) [ "$#" = 2 ] || usage; prefix=$1 out=$2; compiler= sysroot= ;;
    --cross) [ "$#" = 4 ] || usage; compiler=$1 sysroot=$2 prefix=$3 out=$4 ;;
    *) usage ;;
esac
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple absolute paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
[ -f "$prefix/include/sqlite3.h" ] && [ -f "$prefix/lib/libsqlite3.so" ]
probe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
mkdir -p "$out/logs"
run() {
    name=$1; shift
    status=0
    "$@" > "$out/logs/$name.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$out/logs/$name.status"
    if [ "$status" -ne 0 ]; then cat "$out/logs/$name.log" >&2; exit "$status"; fi
}
if [ "$mode" = --cross ]; then
    cc=$compiler/bin/aarch64--netbsd-gcc
    [ "$("$cc" -dumpfullversion)" = 16.2.0 ] && [ "$("$cc" -dumpmachine)" = aarch64--netbsd ]
    crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
    cat > "$out/toolchain.cmake" <<CMAKE
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $cc)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$sysroot/usr/pkg/gcc16/lib -march=armv8-a -Wl,-rpath,/usr/pkg/gcc16/lib")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
CMAKE
    set -- "-DCMAKE_TOOLCHAIN_FILE=$out/toolchain.cmake" '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib'
else
    cc=$(command -v "${CC:-gcc}")
    [ "$("$cc" -dumpfullversion)" = 16.2.0 ] || { echo 'GCC 16.2.0 required.' >&2; exit 2; }
    [ -z "${LD_LIBRARY_PATH:-}" ] && [ -z "${LD_PRELOAD:-}" ] || { echo 'Use an ordinary loader environment.' >&2; exit 2; }
    set -- "-DCMAKE_C_COMPILER=$cc" "-DCMAKE_INSTALL_RPATH=$prefix/lib"
fi
run configure cmake -S "$probe/tests" -B "$out/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DSQLITE_PREFIX="$prefix" -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON "$@"
run build cmake --build "$out/build" --parallel 1
if [ "$mode" = --cross ]; then
    "$compiler/bin/aarch64--netbsd-readelf" -h -d "$out/build/sqlite-contract" > "$out/elf.txt"
    grep 'Machine:.*AArch64' "$out/elf.txt" >/dev/null
    grep 'NEEDED.*\[libsqlite3.so.0\]' "$out/elf.txt" >/dev/null
    echo 'SQLite installed consumer cross-build PASS; execute on EmberBSD separately.'
    exit 0
fi
run ctest ctest --test-dir "$out/build" --no-tests=error --output-on-failure --verbose
for binary in "$out/build/sqlite-contract" "$prefix/bin/sqlite3"; do
    name=$(basename "$binary")
    ldd "$binary" > "$out/logs/$name-linkage.txt"
    if grep -E 'not found' "$out/logs/$name-linkage.txt"; then exit 1; fi
    loaded=$(awk '/libsqlite3[.]so/ {print $3}' "$out/logs/$name-linkage.txt")
    [ -n "$loaded" ] && [ "$(printf '%s\n' "$loaded" | wc -l | tr -d ' ')" = 1 ]
    [ "$(realpath "$loaded")" = "$(realpath "$prefix/lib/libsqlite3.so")" ] || {
        echo 'The consumer loaded SQLite outside the selected prefix.' >&2; exit 1;
    }
done
memcheck=${RUN_MEMCHECK:-1}
case "$memcheck" in 0|1) ;; *) echo 'RUN_MEMCHECK must be 0 or 1.' >&2; exit 2;; esac
printf '%s\n' "$memcheck" > "$out/memcheck-enabled.txt"
if [ "$memcheck" = 1 ]; then
    command -v valgrind >/dev/null
    valgrind --version > "$out/logs/valgrind-version.txt"
    set -- valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
        --errors-for-leak-kinds=definite,indirect,possible --track-origins=yes --error-exitcode=97
    run memcheck-consumer "$@" "$out/build/sqlite-contract" "$out/memcheck.db"
    run memcheck-cli "$@" "$prefix/bin/sqlite3" :memory: \
        "CREATE VIRTUAL TABLE docs USING fts5(body); INSERT INTO docs VALUES('loop closure'); SELECT count(*) FROM docs WHERE docs MATCH 'closure'; SELECT json_extract('{\"answer\":42}', '$.answer'); PRAGMA integrity_check;"
    status=0
    "$@" "$prefix/bin/sqlite3" :memory: 'SELECT * FROM missing_table;' \
        > "$out/logs/memcheck-cli-invalid.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$out/logs/memcheck-cli-invalid.status"
    [ "$status" = 1 ] || { echo 'Unexpected invalid-SQL/Memcheck status.' >&2; exit 1; }
    grep 'ERROR SUMMARY: 0 errors' "$out/logs/memcheck-cli-invalid.log" >/dev/null
fi
if [ "$memcheck" = 1 ]; then
    echo 'PASS installed SQLite C/CLI contracts and three native Memcheck runs'
else
    echo 'PASS installed SQLite C/CLI contracts; native Memcheck was explicitly disabled'
fi
