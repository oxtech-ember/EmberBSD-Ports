#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed Polkit/ConsoleKit API regression.
set -eu
[ "$#" = 3 ] || { echo 'Usage: build-ids.sh CROSS_TOOLS SYSROOT NEW_WORK' >&2; exit 2; }
tools=$1 sysroot=$2 work=$3
: "${PKG_CONFIG:?Set native pkg-config}"
for path in "$tools" "$sysroot" "$work" "$PKG_CONFIG"; do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) exit 2;; esac
done
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$work"
PKG_CONFIG_SYSROOT_DIR=$sysroot
PKG_CONFIG_LIBDIR=$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/pkg/share/pkgconfig:$sysroot/usr/lib/pkgconfig
PKG_CONFIG_PATH=
export PKG_CONFIG_SYSROOT_DIR PKG_CONFIG_LIBDIR PKG_CONFIG_PATH
cflags=$("$PKG_CONFIG" --cflags polkit-gobject-1)
libs=$("$PKG_CONFIG" --libs polkit-gobject-1)
"$tools/bin/aarch64--netbsd-gcc" --sysroot="$sysroot" \
    -B"$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
    -L"$sysroot/usr/pkg/gcc16/lib" -L"$sysroot/usr/pkg/lib" \
    -Wl,-rpath,/usr/pkg/lib -Wl,-rpath,/usr/pkg/gcc16/lib \
    -Wall -Wextra -Werror $cflags "$src/ids.c" $libs -o "$work/ids"
shasum -a 256 "$work/ids" "$src/ids.c" "$0" > "$work/outputs.sha256"
