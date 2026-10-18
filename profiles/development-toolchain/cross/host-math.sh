#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted, isolated current GCC host prerequisites.
set -eu
host_mode=gcc16
if [ "${1:-}" = --native-clang ]; then host_mode=native-clang; shift; fi
[ "$#" -eq 3 ] || {
    echo 'Usage: host-math.sh [--native-clang] ARCHIVE_DIRECTORY NETBSD_TOOLDIR NEW_WORK' >&2
    exit 2
}
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
delta=$here/patches/gmp-t-rand-varargs.patch
[ "$(shasum -a 256 "$delta" | awk '{print $1}')" = \
    7ac7687eee380a35f2289baf2bf964c42b82c02bca2272aef6e2e46b23e87736 ] || {
    echo 'GMP test patch SHA256 mismatch.' >&2; exit 1;
}
archives=$1 tools=$2 work=$3
host_cc=${HOST_CC:-gcc-16}
host_cxx=${HOST_CXX:-g++-16}
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use paths without whitespace or shell metacharacters.' >&2; exit 2;; esac
done
if [ "${CROSS_JOBS+x}" = x ]; then
    jobs=$CROSS_JOBS
else
    jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null) || {
        echo 'Cannot detect host CPU count; set CROSS_JOBS explicitly.' >&2; exit 2;
    }
fi
case "$jobs" in ''|*[!0-9]*) jobs=0;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'CROSS_JOBS must be positive.' >&2; exit 2; }
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'NEW_WORK already exists.' >&2; exit 2; }
[ -x "$tools/bin/nbgmake" ] || { echo 'Bootstrap GNU make missing.' >&2; exit 2; }
for compiler in "$host_cc" "$host_cxx"; do
    command -v "$compiler" >/dev/null 2>&1 || {
        echo "Host GCC16 compiler missing: $compiler" >&2; exit 2;
    }
    if [ "$host_mode" = native-clang ]; then
        identity=$("$compiler" --version)
        printf '%s\n' "$identity" | grep -Eq '^(Apple )?clang version [0-9]+' || {
            echo 'Native Clang is required for the explicit host-only mode.' >&2; exit 2;
        }
        compiler_target=$("$compiler" -dumpmachine)
        case "$(uname -m):$compiler_target" in
            arm64:arm64-apple-*|arm64:aarch64-apple-*|aarch64:aarch64-*|x86_64:x86_64-*) ;;
            *) echo 'Host-only Clang target differs from the development host.' >&2; exit 2;;
        esac
    else
        version=$("$compiler" -dumpfullversion) || {
            echo "Cannot identify host GCC16 compiler: $compiler" >&2; exit 2;
        }
        case "$version" in 16.*) ;; *) echo "GCC 16 host compiler required: $compiler ($version)" >&2; exit 2;; esac
    fi
done
mkdir -p "$archives"
for item in gmp:6.3.0:tar.xz mpfr:4.2.2:tar.bz2 mpc:1.4.1:tar.xz; do
    name=${item%%:*}; rest=${item#*:}; version=${rest%%:*}; suffix=${rest#*:}
    archive=$archives/$name-$version.$suffix
    expected=$(awk -F '\t' -v name="$name" -v version="$version" \
        '$1 == name && $2 == version {print $4}' "$here/host-sources.tsv" "$here/../sources.tsv")
    if [ ! -e "$archive" ]; then
        url=$(awk -F '\t' -v name="$name" -v version="$version" \
            '$1 == name && $2 == version {print $3}' "$here/host-sources.tsv" "$here/../sources.tsv")
        [ -n "$url" ] || { echo 'Missing source URL.' >&2; exit 1; }
        curl -fL "$url" -o "$archive.part"
        [ "$(shasum -a 256 "$archive.part" | awk '{print $1}')" = "$expected" ] || {
            echo "$name download SHA256 mismatch." >&2; exit 1;
        }
        mv "$archive.part" "$archive"
    fi
    [ -f "$archive" ] && [ -n "$expected" ] && \
        [ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$expected" ] || {
        echo "$name archive SHA256 mismatch or missing archive." >&2; exit 1;
    }
done
mkdir -p "$work"
work=$(CDPATH= cd -- "$work" && pwd -P)
prefix=$work/prefix
mkdir "$prefix"
{
    uname -srm
    printf 'host_compiler_mode=%s\n' "$host_mode"
    printf 'host_cc=%s\nhost_cxx=%s\ncflags=%s\ncxxflags=%s\n' \
        "$host_cc" "$host_cxx" '-O2 -std=gnu17' '-O2'
    "$host_cc" --version
    "$host_cc" -dumpmachine
    "$host_cxx" --version
    printf 'jobs=%s\n' "$jobs"
    shasum -a 256 "$delta"
} > "$work/inputs.txt"
unset CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH
for item in gmp:6.3.0:tar.xz mpfr:4.2.2:tar.bz2 mpc:1.4.1:tar.xz; do
    name=${item%%:*}; rest=${item#*:}; version=${rest%%:*}; suffix=${rest#*:}
    archive=$archives/$name-$version.$suffix
    mkdir "$work/$name-src" "$work/$name-build"
    shasum -a 256 "$archive" >> "$work/inputs.txt"
    tar -xf "$archive" --strip-components=1 -C "$work/$name-src"
    if [ "$name" = gmp ]; then
        patch -f -N -F 0 -p1 -d "$work/$name-src" < "$delta" \
            > "$work/gmp-patch.log" 2>&1
    fi
    (
        cd "$work/$name-build"
        set -- --prefix="$prefix" --disable-shared --enable-static
        case "$name" in
            mpfr) set -- "$@" --with-gmp="$prefix";;
            mpc) set -- "$@" --with-gmp="$prefix" --with-mpfr="$prefix";;
        esac
        # GMP 6.3's configure probes use pre-C23 empty parameter lists.
        # Select their supported C dialect without changing the compiler.
        CC=$host_cc CXX=$host_cxx CFLAGS='-O2 -std=gnu17' CXXFLAGS=-O2 \
            "$work/$name-src/configure" "$@" > "$work/$name-configure.log" 2>&1
        "$tools/bin/nbgmake" -j"$jobs" > "$work/$name-build.log" 2>&1
        "$tools/bin/nbgmake" -j"$jobs" check > "$work/$name-check.log" 2>&1
        "$tools/bin/nbgmake" install > "$work/$name-install.log" 2>&1
    )
done
"$host_cc" -O2 -I"$prefix/include" "$here/tests/host-gmp.c" \
    "$prefix/lib/libgmp.a" -o "$work/host-gmp"
"$work/host-gmp"
"$work/host-gmp" timer
echo "GCC host prerequisites built and tested: $prefix"
