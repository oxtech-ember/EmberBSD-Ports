#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Build the genuine upstream host resource tool.
set -eu
umask 022
[ "$#" = 2 ] || { echo 'Usage: build-resource-tool.sh ARCHIVE NEW_OUTPUT' >&2; exit 2; }
archive=$1 out=$2
for path do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
[ "$(gcc -dumpfullversion)" = 16.2.0 ] && [ "$(g++ -dumpfullversion)" = 16.2.0 ]
ports=$(CDPATH= cd "$(dirname "$0")/../.." && pwd -P)
recipe=$ports/pkgsrc/local-robotics/rtabmap
printf '%s  %s\n' 587d8936b8d8669b196d500df80e373417e0c4c033309a2e4a0b84a627117284 "$archive" | sha256sum -c -
mkdir -p "$out/source" "$out/logs"
tar -xf "$archive" --strip-components=1 -C "$out/source"
for delta in "$recipe/patches/"patch-*; do
    patch --batch --forward -F 0 -d "$out/source" -p1 < "$delta" >> "$out/logs/patches.log" 2>&1
done
# Upstream's early resource-only branch does not set the Android platform.
cmake -S "$out/source" -B "$out/build" -G Ninja -DANDROID_PREBUILD=ON \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_C_COMPILER="$(command -v gcc)" -DCMAKE_CXX_COMPILER="$(command -v g++)" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel 1 --target rtabmap-res_tool > "$out/logs/build.log" 2>&1
sha256sum "$archive" "$0" "$recipe/patches/"patch-* "$out/build/bin/rtabmap-res_tool" > "$out/inputs.sha256"
echo "Native RTABMAP_RES_TOOL=$out/build/bin/rtabmap-res_tool"
