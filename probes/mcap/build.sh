#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
umask 022
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: build.sh ABS_NEW_WORK [ABS_CACHE]' >&2; exit 2; }
work=$1
for directory in "$@"; do
    case "$directory" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
    case "$directory" in *[!a-zA-Z0-9_./-]*) echo 'Use paths without whitespace or shell metacharacters.' >&2; exit 2 ;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work path already exists.' >&2; exit 2; }
jobs=${JOBS:-1}
case "$jobs" in ''|0|*[!0-9]*) echo 'JOBS must be positive.' >&2; exit 2 ;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'JOBS must be positive.' >&2; exit 2; }
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
for tool in cmake ninja tar; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done
if command -v sha256 >/dev/null; then
    digest() { sha256 -q "$1"; }
else
    command -v shasum >/dev/null || { echo 'sha256 or shasum required.' >&2; exit 2; }
    digest() { shasum -a 256 "$1" | cut -d ' ' -f 1; }
fi
[ "$#" = 2 ] || command -v curl >/dev/null
mkdir "$work"
mkdir "$work/src" "$work/archives" "$work/logs"
prefix=$work/install
run()
{
    stage=$1
    shift
    printf '%s\n' "$stage"
    status=0
    "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then
        tail -60 "$work/logs/$stage.log" >&2
        exit "$status"
    fi
}
# Validate every source before extracting any archive.
while read -r name expected url; do
    if [ "$#" = 2 ]; then
        cp "$2/$name" "$work/archives/$name"
    else
        curl -fLsS --connect-timeout 20 --max-time 900 "$url" -o "$work/archives/$name"
    fi
    actual=$(digest "$work/archives/$name")
    [ "$actual" = "$expected" ] || { echo "Checksum mismatch: $name" >&2; exit 2; }
    printf '%s %s %s\n' "$name" "$actual" "$url" >> "$work/logs/sources.txt"
done < "$recipe/sources.tsv"
while read -r name expected url; do
    tar -xf "$work/archives/$name" -C "$work/src"
done < "$recipe/sources.tsv"
{ uname -a; cmake --version; ninja --version; } > "$work/logs/tools.txt"
run lz4-configure cmake -S "$work/src/lz4-1.11.1/build/cmake" -B "$work/lz4-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DBUILD_SHARED_LIBS=ON -DBUILD_STATIC_LIBS=OFF -DLZ4_BUILD_CLI=OFF
run lz4-build cmake --build "$work/lz4-build" --parallel "$jobs"
run lz4-install cmake --install "$work/lz4-build"
run zstd-configure cmake -S "$work/src/zstd-1.5.7/build/cmake" -B "$work/zstd-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DZSTD_BUILD_SHARED=ON -DZSTD_BUILD_STATIC=OFF -DZSTD_BUILD_PROGRAMS=OFF \
    -DZSTD_BUILD_TESTS=OFF -DZSTD_MULTITHREAD_SUPPORT=ON
run zstd-build cmake --build "$work/zstd-build" --parallel "$jobs"
run zstd-install cmake --install "$work/zstd-build"
# Upstream MCAP is a header-only C++ library; consumers compile its implementation once.
mkdir -p "$prefix/include" "$prefix/lib/pkgconfig" "$prefix/share/ember-mcap/licenses"
cp -R "$work/src/mcap-releases-cpp-v2.1.3/cpp/mcap/include/mcap" "$prefix/include/"
cat > "$prefix/lib/pkgconfig/mcap.pc" <<PC
prefix=$prefix
includedir=\${prefix}/include
Name: MCAP
Description: MCAP C++ header-only recording and indexed reading library
Version: 2.1.3
Requires: liblz4 = 1.11.1, libzstd = 1.5.7
Cflags: -I\${includedir}
PC
cp "$recipe/sources.tsv" "$recipe/PROVENANCE.md" "$prefix/share/ember-mcap/"
cp "$work/src/mcap-releases-cpp-v2.1.3/LICENSE" "$prefix/share/ember-mcap/licenses/MCAP-MIT"
cp "$work/src/lz4-1.11.1/lib/LICENSE" "$prefix/share/ember-mcap/licenses/LZ4-BSD-2-Clause"
cp "$work/src/zstd-1.5.7/LICENSE" "$prefix/share/ember-mcap/licenses/Zstd-BSD-3-Clause"
echo "Installed in $prefix; run test.sh next."
