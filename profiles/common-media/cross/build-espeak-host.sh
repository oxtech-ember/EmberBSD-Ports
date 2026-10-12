#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Private native data compiler, never a target package.
set -eu
[ "$#" = 2 ] || { echo 'Usage: build-espeak-host.sh DISTFILES NEW_WORK' >&2; exit 2; }
: "${AUTORECONF:?Set native autoreconf}" "${GMAKE:?Set native GNU make}"
CC=${CC:-cc} CXX=${CXX:-c++} JOBS=${JOBS:-2}
case "$JOBS" in ''|*[!0-9]*|0) exit 2;; esac
for path in "$1" "$2"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Unsupported path characters' >&2; exit 2;; esac
done
# Generated tables contain native integer fields. Other host ABIs need acceptance.
case "$(uname -s):$(uname -m)" in Darwin:arm64) ;; *) echo 'This generator recipe is accepted only on macOS/arm64' >&2; exit 2;; esac
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
archive=$1/espeak-ng-1.52.0.tar.gz
expected=$(awk -F '\t' '$1=="audio/espeak-ng" { print $3 }' "$profile/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$expected" ]
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
tar -xf "$archive" -C "$work"
src=$work/espeak-ng-1.52.0
mkdir "$work/build"
unset CFLAGS CXXFLAGS CPPFLAGS LDFLAGS LD_LIBRARY_PATH PKG_CONFIG_SYSROOT_DIR PKG_CONFIG_LIBDIR PKG_CONFIG_PATH
# The autotools path omits upstream's macOS endian compatibility include.
# Expose only endian.h; global compatibility wctype overrides break libc++.
mkdir "$work/compat"
ln -s "$src/src/include/compat/endian.h" "$work/compat/endian.h"
CPPFLAGS="-I$work/compat"
export CC CXX CPPFLAGS
# Match the upstream/pkgsrc preparation without copying target build products.
(cd "$src" && touch AUTHORS NEWS && "$AUTORECONF" -fi) > "$work/autoreconf.log" 2>&1
(cd "$work/build" && "$src/configure" --prefix="$work/private" \
    --without-pcaudiolib --without-sonic --with-mbrola --disable-shared \
    --disable-rpath) > "$work/configure.log" 2>&1
"$GMAKE" -C "$work/build" -j "$JOBS" src/espeak-ng > "$work/build.log" 2>&1
"$work/build/src/espeak-ng" --version > "$work/version.txt" 2>&1
grep '1.52.0' "$work/version.txt" >/dev/null
file "$work/build/src/espeak-ng" > "$work/format.txt"
grep 'Mach-O.*arm64' "$work/format.txt" >/dev/null
shasum -a 256 "$archive" "$0" "$work/build/src/espeak-ng" > "$work/inputs-output.sha256"
{ "$CC" --version; "$CXX" --version; "$AUTORECONF" --version; "$GMAKE" --version; } > "$work/tool-versions.txt"
printf 'Built native data compiler: %s\n' "$work/build/src/espeak-ng"
