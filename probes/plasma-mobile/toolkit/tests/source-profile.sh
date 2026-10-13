#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted Qt/KF source and exporter regression.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 VERIFIED_DISTFILES NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
toolkit=$root/probes/plasma-mobile/toolkit
distfiles=$(CDPATH= cd -- "$1" && pwd)
sh "$toolkit/tests/verify-sources.sh" "$toolkit" "$distfiles" "$2"
work=$(CDPATH= cd -- "$2" && pwd)
export DIGEST=$work/digest
verifier=$root/upstream/pkgsrc/mk/checksum/checksum.awk
sh "$toolkit/tests/portal-feature.sh" "$work/source/qtbase-everywhere-src-6.12.0" "$work/portal-feature"
archive=qtspeech-everywhere-src-6.12.0.tar.xz
cp "$distfiles/$archive" "$work/$archive"
printf x >> "$work/$archive"
if (cd "$work" && awk -f "$verifier" -- "$toolkit/recipes/audio/qt6-qtspeech/distinfo" "$archive") > "$work/corrupt.log" 2>&1; then exit 1; fi
pkg=$toolkit/recipes/x11/qt6-qtbase
name=patch-qt__cmdline.cmake
if patch -f -N -F 0 -p0 -d "$work/source/qtbase-everywhere-src-6.12.0" < "$pkg/patches/$name" > "$work/repeated.log" 2>&1; then exit 1; fi
if awk -f "$verifier" -- -p "$pkg/distinfo" "$work/$name" > "$work/missing.log" 2>&1; then exit 1; fi
raw=$(shasum -a 1 "$pkg/patches/$name" | awk '{ print $1 }')
sed "s/^SHA1 ($name) = .*/SHA1 ($name) = $raw/" "$pkg/distinfo" > "$work/raw-distinfo"
if awk -f "$verifier" -- -p "$work/raw-distinfo" "$pkg/patches/$name" > "$work/raw.log" 2>&1; then exit 1; fi
sh "$toolkit/tests/mkspecs-preservation.sh" "$toolkit/recipes/x11/qt6-qtbase" "$work/mkspecs-preservation"
sh "$toolkit/tests/target-metadata.sh" "$toolkit/recipes/x11/qt6-qtbase" "$work/target-metadata"
sh "$toolkit/tests/selection.sh" "$toolkit" "$work/selection"
sh "$toolkit/tests/dependencies.sh" "$work/dependencies"
sh "$toolkit/tests/ffmpeg-vaapi.sh" "$work/source/qtmultimedia-everywhere-src-6.12.0" "$work/ffmpeg"
sh "$root/scripts/prepare-pkgsrc.sh" "$work/pkgsrc" plasma-mobile > "$work/export.log"
sh "$toolkit/validate.sh" --inventory "$toolkit" > "$work/exported-recipes.tsv"
while IFS="$(printf '\t')" read -r recipe owner kind; do
    if [ "$kind" = overlay ]; then
        (cd "$toolkit/recipes/$recipe" && find . -type f -print) | while IFS= read -r file; do
            cmp "$toolkit/recipes/$recipe/$file" "$work/pkgsrc/$recipe/$file"
        done
        cmp "$root/upstream/pkgsrc/$recipe/Makefile" "$work/pkgsrc/$recipe/Makefile"
    else
        diff -qr "$toolkit/recipes/$recipe" "$work/pkgsrc/$recipe"
    fi
done < "$work/exported-recipes.tsv"
cmp "$toolkit/sources.tsv" "$work/pkgsrc/EMBERBSD-PLASMA-TOOLKIT-SOURCES"
cmp "$toolkit/source-owners.tsv" "$work/pkgsrc/EMBERBSD-PLASMA-TOOLKIT-SOURCE-OWNERS"
for recipe in lang/python314 devel/meson lang/llvm lang/clang devel/lld devel/py-llvm-lit; do
    diff -qr "$root/profiles/common-build-tools/recipes/$recipe" "$work/pkgsrc/$recipe"
done
cmp "$root/profiles/common-build-tools/mk.conf" "$work/pkgsrc/EMBERBSD-COMMON-TOOLS-MK.CONF"
cmp "$root/profiles/development-toolchain/mk.conf" "$work/pkgsrc/EMBERBSD-DEVELOPMENT-MK.CONF"
cmp "$toolkit/mk.conf" "$work/pkgsrc/EMBERBSD-PLASMA-TOOLKIT-MK.CONF"
for file in meta-pkgs/qt6/Makefile.common meta-pkgs/kde/kf6.mk meta-pkgs/kde/plasma6.mk; do
    cmp "$toolkit/shared/$file" "$work/pkgsrc/$file"
done
if sh "$root/scripts/prepare-pkgsrc.sh" "$work/pkgsrc" plasma-mobile > "$work/existing.log" 2>&1; then exit 1; fi
echo 'PASS: toolkit sources, patches, selection and export; native packages/PLIST/runtime remain pending'
