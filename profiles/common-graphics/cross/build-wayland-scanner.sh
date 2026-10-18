#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), build only the matching host generator.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 WAYLAND_ARCHIVE NEW_ABSOLUTE_WORK" >&2; exit 2; }
archive=$1 work=$2
recipe=$(CDPATH= cd -- "$(dirname -- "$0")/../recipes/devel/wayland" && pwd)
: "${HOST_PYTHON:?Set the current build-host Python executable}"
: "${MESON:?Set the current upstream meson.py}"
: "${NINJA:?Set the build-host Ninja executable}"
: "${PKG_CONFIG:?Set the build-host pkgconf executable}"
HOST_CC=${HOST_CC:-/usr/bin/cc}
for path in "$archive" "$work" "$HOST_PYTHON" "$MESON" "$NINJA" "$PKG_CONFIG" "$HOST_CC"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) echo 'Use paths without whitespace or shell metacharacters' >&2; exit 2;; esac
done
for tool in "$HOST_PYTHON" "$NINJA" "$PKG_CONFIG" "$HOST_CC"; do [ -x "$tool" ]; done
hash() { shasum -a 256 "$1" | awk '{print $1}'; }
[ "$(hash "$archive")" = 64176eaa46e4969903e286f8e5ef8331affc17fdf03ac9b58381d2b23162b7a3 ]
mkdir "$work"
mkdir "$work/source" "$work/bin"
tar -xf "$archive" --strip-components=1 -C "$work/source"
for name in $(awk '/^SHA1 \(patch-/ {gsub(/[()]/,"",$2); print $2}' "$recipe/distinfo"); do
    expected=$(awk -v n="($name)" '$1=="SHA1" && $2==n {print $4}' "$recipe/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$recipe/patches/$name" | shasum -a 1 | awk '{print $1}')
    [ "$actual" = "$expected" ]
    patch -f -N -F 0 -d "$work/source" -p0 < "$recipe/patches/$name" >> "$work/patch.log"
done
ln -s "$HOST_PYTHON" "$work/bin/python3"
ln -s "$NINJA" "$work/bin/ninja"
PATH="$work/bin:$PATH"
export PATH PKG_CONFIG
{
    shasum -a 256 "$archive" "$0" "$HOST_PYTHON" "$MESON" "$NINJA" "$PKG_CONFIG" "$HOST_CC"
    "$HOST_PYTHON" --version
    "$HOST_PYTHON" "$MESON" --version
    "$NINJA" --version
    "$PKG_CONFIG" --version
    "$HOST_CC" --version
} > "$work/inputs.txt"
printf 'CFLAGS=%s\nCPPFLAGS=%s\nLDFLAGS=%s\n' \
    "${CFLAGS-}" "${CPPFLAGS-}" "${LDFLAGS-}" > "$work/compiler-flags.txt"
(cd "$work/source" && find . -type f -exec shasum -a 256 {} \;) > "$work/source.sha256"
CC="$HOST_CC" "$HOST_PYTHON" "$MESON" setup "$work/build" "$work/source" \
    --prefix="$work/prefix" --libdir=lib --wrap-mode=nodownload \
    -Dlibraries=false -Dscanner=true -Dtests=false \
    -Ddocumentation=false -Ddtd_validation=true > "$work/configure.log" 2>&1
"$NINJA" -C "$work/build" -j2 > "$work/build.log" 2>&1
"$HOST_PYTHON" "$MESON" install -C "$work/build" > "$work/install.log" 2>&1
[ "$("$work/prefix/bin/wayland-scanner" --version 2>&1)" = 'wayland-scanner 1.26.0' ]
[ -s "$work/prefix/lib/pkgconfig/wayland-scanner.pc" ]
# Run upstream's actual scanner golden-output and malformed-input tests.
mkdir "$work/scanner-output"
TEST_DATA_DIR="$work/source/tests/data" TEST_OUTPUT_DIR="$work/scanner-output" \
    SED="$(command -v sed)" WAYLAND_SCANNER="$work/prefix/bin/wayland-scanner" \
    sh "$work/source/tests/scanner-test.sh" > "$work/scanner-test.log" 2>&1
(cd "$work/prefix" && find . -type f -exec shasum -a 256 {} \;) > "$work/installed.sha256"
printf 'PASS: Wayland 1.26.0 host scanner and upstream scanner tests: %s\n' "$work/prefix/bin/wayland-scanner"
