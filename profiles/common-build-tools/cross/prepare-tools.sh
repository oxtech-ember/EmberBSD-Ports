#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); compose existing host tools without rebuilding.
set -eu
usage() {
    echo "Usage: $0 [--target aarch64|amd64] GCC16_PREFIX NETBSD_TOOLDIR NEW_TOOLDIR" >&2
    exit 2
}
profiles=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
. "$profiles/development-toolchain/cross/target-options.sh"
[ "$#" = 3 ] || usage
compiler=$1 os_tools=$2 output=$3
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) echo 'Use paths without shell metacharacters.' >&2; exit 2 ;; esac
done
[ ! -e "$output" ] && [ ! -L "$output" ] || { echo 'Output already exists.' >&2; exit 2; }
[ "$("$compiler/bin/$triplet-gcc" -dumpmachine)" = "$triplet" ]
[ "$("$compiler/bin/$triplet-gcc" -dumpfullversion)" = 16.2.0 ]
for name in gcc g++ cpp gcc-ar gcc-nm gcc-ranlib ar as ld nm objcopy objdump ranlib readelf strip; do
    [ -x "$compiler/bin/$triplet-$name" ] || { echo "Missing cross tool: $name" >&2; exit 2; }
done
[ -x "$os_tools/bin/$triplet-install" ] || { echo 'Missing NetBSD host install tool.' >&2; exit 2; }
mkdir -p "$output/bin"
for name in gcc g++ cpp gcc-ar gcc-nm gcc-ranlib ar as ld nm objcopy objdump ranlib readelf strip; do
    ln -s "$compiler/bin/$triplet-$name" "$output/bin/$triplet-$name"
done
ln -s "$os_tools/bin/$triplet-install" "$output/bin/$triplet-install"
echo 'Prepared GCC16 cross tools with the NetBSD host install utility.'
