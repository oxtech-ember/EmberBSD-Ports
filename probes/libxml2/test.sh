#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 1 ] || { echo 'Usage: test.sh ABS_WORK' >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) exit 2 ;; esac
case "$work" in *[!a-zA-Z0-9_./-]*) exit 2 ;; esac
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
prefix=$work/install
cmp "$recipe/sources.tsv" "$prefix/share/ember-libxml2/sources.tsv" >/dev/null
cmp "$recipe/patches.tsv" "$prefix/share/ember-libxml2/patches.tsv" >/dev/null
cmake=${CMAKE:-cmake}
export LD_LIBRARY_PATH="$prefix/lib" DYLD_LIBRARY_PATH="$prefix/lib"
ctest --test-dir "$work/build" --output-on-failure > "$work/logs/upstream-tests.log" 2>&1
"$cmake" -S "$recipe/tests" -B "$work/test-build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DXML_PREFIX="$prefix" -DCMAKE_BUILD_RPATH="$prefix/lib" > "$work/logs/test-configure.log" 2>&1
"$cmake" --build "$work/test-build" --parallel 1 > "$work/logs/test-build.log" 2>&1
ctest --test-dir "$work/test-build" --output-on-failure -V > "$work/logs/test.log" 2>&1
case "$(uname -s)" in
    Darwin) otool -L "$work/test-build/xml-contract" > "$work/logs/linked-libraries.txt" ;;
    NetBSD) ldd "$work/test-build/xml-contract" > "$work/logs/linked-libraries.txt" ;;
esac
find "$prefix" -type f | sort | while IFS= read -r file; do
    if command -v sha256 >/dev/null; then printf '%s %s\n' "$(sha256 -q "$file")" "$file";
    else shasum -a 256 "$file"; fi
done > "$work/logs/installed-sha256.txt"
cat "$work/logs/test.log"
