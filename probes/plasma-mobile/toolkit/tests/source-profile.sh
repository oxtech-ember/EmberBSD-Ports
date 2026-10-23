#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted Qt/KF source regression.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 VERIFIED_DISTFILES NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
toolkit=$root/probes/plasma-mobile/toolkit
recipes=$root/pkgsrc
distfiles=$(CDPATH= cd -- "$1" && pwd)
sh "$toolkit/tests/verify-sources.sh" "$toolkit" "$distfiles" "$2"
work=$(CDPATH= cd -- "$2" && pwd)
export DIGEST=$work/digest
verifier=$root/upstream/pkgsrc/mk/checksum/checksum.awk
sh "$toolkit/tests/portal-feature.sh" "$work/source/qtbase-everywhere-src-6.12.0" "$work/portal-feature"
archive=qtspeech-everywhere-src-6.12.0.tar.xz
cp "$distfiles/$archive" "$work/$archive"
printf x >> "$work/$archive"
if (cd "$work" && awk -f "$verifier" -- "$recipes/audio/qt6-qtspeech/distinfo" "$archive") > "$work/corrupt.log" 2>&1; then exit 1; fi
pkg=$recipes/x11/qt6-qtbase
name=patch-qt__cmdline.cmake
if patch -f -N -F 0 -p0 -d "$work/source/qtbase-everywhere-src-6.12.0" < "$pkg/patches/$name" > "$work/repeated.log" 2>&1; then exit 1; fi
if awk -f "$verifier" -- -p "$pkg/distinfo" "$work/$name" > "$work/missing.log" 2>&1; then exit 1; fi
raw=$(shasum -a 1 "$pkg/patches/$name" | awk '{ print $1 }')
sed "s/^SHA1 ($name) = .*/SHA1 ($name) = $raw/" "$pkg/distinfo" > "$work/raw-distinfo"
if awk -f "$verifier" -- -p "$work/raw-distinfo" "$pkg/patches/$name" > "$work/raw.log" 2>&1; then exit 1; fi
sh "$toolkit/tests/mkspecs-preservation.sh" "$recipes/x11/qt6-qtbase" "$work/mkspecs-preservation"
sh "$toolkit/tests/target-metadata.sh" "$recipes/x11/qt6-qtbase" "$work/target-metadata"
sh "$toolkit/tests/selection.sh" "$toolkit" "$work/selection"
sh "$toolkit/tests/dependencies.sh" "$work/dependencies"
sh "$toolkit/tests/ffmpeg-vaapi.sh" "$work/source/qtmultimedia-everywhere-src-6.12.0" "$work/ffmpeg"
echo 'PASS: toolkit sources, patches and selection; export, packages/PLIST/runtime remain pending'
