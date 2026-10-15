#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; reuse the native C/C++ acceptance sources for a cross build.
set -eu
usage() { echo 'Usage: compile-tests.sh [--target aarch64|amd64] CROSS_PREFIX SYSROOT NEW_OUTPUT' >&2; exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
. "$here/target-options.sh"
[ "$#" -eq 3 ] || usage
prefix=$1 sysroot=$2 out=$3
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output already exists.' >&2; exit 2; }
source=$(CDPATH= cd -- "$(dirname -- "$0")/../tests" && pwd -P)
cross_source=$(CDPATH= cd -- "$(dirname -- "$0")/tests" && pwd -P)
cc=$prefix/bin/$triplet-gcc
cxx=$prefix/bin/$triplet-g++
for compiler in "$cc" "$cxx"; do
    [ -x "$compiler" ] && [ "$("$compiler" -dumpfullversion)" = 16.2.0 ] && \
        [ "$("$compiler" -dumpmachine)" = "$triplet" ] || {
        echo 'Selected target GCC16 compiler mismatch.' >&2; exit 2;
    }
done
[ -f "$sysroot/usr/include/stddef.h" ] && \
    [ -f "$sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/crtbegin.o" ] && \
    [ -d "$sysroot/usr/pkg/gcc16/include/c++/$triplet" ] || {
    echo 'Selected target GCC16 runtime missing.' >&2; exit 2;
}
[ -x "$prefix/bin/$triplet-readelf" ] || { echo 'Selected target readelf missing.' >&2; exit 2; }
root=$(CDPATH= cd -- "$sysroot" && pwd -P)
for library in libstdc++.so.7 libgcc_s.so.1; do
    actual=$(realpath "$sysroot/usr/pkg/gcc16/lib/$library") || exit 2
    case "$actual" in "$root/usr/pkg/gcc16/"*) ;; *) echo 'Target runtime escapes the sysroot GCC16 prefix.' >&2; exit 2;; esac
    [ -f "$actual" ] || { echo 'Selected target GCC16 shared runtime missing.' >&2; exit 2; }
done
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
mkdir "$out"
printf '%s\n' "$target" > "$out/target.txt"
for item in libstdc++.so:libstdc++.so.7 libgcc_s.so:libgcc_s.so.1; do
    library=${item%:*} file=${item#*:}
    digest=$(shasum -a 256 "$sysroot/usr/pkg/gcc16/lib/$file" | awk '{print $1}')
    printf '%s\t%s\n' "$library" "$digest"
done > "$out/runtime-sha256.tsv"
"$cc" -v 2> "$out/compiler.txt"
set -- --sysroot="$sysroot" -B"$sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/" \
    -L"$sysroot/usr/pkg/gcc16/lib" -Wl,-rpath,/usr/pkg/gcc16/lib
"$cc" "$@" -std=c11 -O2 -Wall -Wextra -Werror -pthread "$source/atomic-tls.c" -o "$out/atomic-tls"
"$cc" "$@" -std=c11 -O2 -flto -Wall -Wextra -Werror -pthread "$source/atomic-tls.c" -o "$out/atomic-tls-lto"
set -- "$@" -isystem "$sysroot/usr/pkg/gcc16/include/c++" \
    -isystem "$sysroot/usr/pkg/gcc16/include/c++/$triplet" \
    -isystem "$sysroot/usr/pkg/gcc16/include/c++/backward"
"$cxx" "$@" -std=c++20 -O3 -Wall -Wextra -Werror \
    -c "$cross_source/float-constexpr.cc" -o "$out/float-constexpr.o"
"$cxx" "$@" -std=c++20 -O2 -Wall -Wextra -Werror -fPIC -shared \
    "$source/boundary.cc" -Wl,-soname,libboundary.so -o "$out/libboundary.so"
"$cxx" "$@" -std=c++20 -O2 -Wall -Wextra -Werror -pthread \
    "$source/boundary-main.cc" -L"$out" '-Wl,-rpath,$ORIGIN' -lboundary -o "$out/boundary"
"$prefix/bin/$triplet-readelf" -d "$out/boundary" "$out/libboundary.so" > "$out/dynamic.txt"
if grep -F -e "$prefix" -e "$sysroot" -e "$out" "$out/dynamic.txt" | grep -E 'RPATH|RUNPATH|NEEDED'; then
    echo 'Host path leaked into target dynamic dependencies.' >&2; exit 1
fi
cp "$here/check-runtime.sh" "$out/"
cp "$source/../cross/run-target.sh" "$out/"
cp "$here/target-options.sh" "$out/"
echo "Cross-compiled tests: $out; run run-target.sh on EmberBSD."
