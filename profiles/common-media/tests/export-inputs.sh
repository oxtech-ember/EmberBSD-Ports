#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Rejection must precede destination creation; the real exporter is executed.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: $0 NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
mkdir -p "$work/source/profiles" "$work/source/scripts"
cp "$root/scripts/prepare-pkgsrc.sh" "$work/source/scripts/"
cp -R "$root/profiles/common-media" "$work/source/profiles/"
for path in .git upstream probes pkgsrc; do ln -s "$root/$path" "$work/source/$path"; done
for path in common-build-tools common-graphics development-toolchain; do
    ln -s "$root/profiles/$path" "$work/source/profiles/$path"
done
profile=$work/source/profiles/common-media
pkg=$profile/recipes/multimedia/ffmpeg9
negative() {
    for mode in common-media plasma-mobile; do
        if sh "$work/source/scripts/prepare-pkgsrc.sh" "$work/rejected" "$mode" > "$work/$1-$mode.log" 2>&1; then exit 1; fi
        [ ! -e "$work/rejected" ]
    done
}
mv "$pkg/Makefile" "$pkg/Makefile.saved"
negative missing-recipe
mv "$pkg/Makefile.saved" "$pkg/Makefile"
cp "$pkg/patches/patch-zz-sunau-current-api" "$work/saved-patch"
printf '\nchanged\n' >> "$pkg/patches/patch-zz-sunau-current-api"
negative altered-patch
cp "$work/saved-patch" "$pkg/patches/patch-zz-sunau-current-api"
cp "$pkg/distinfo" "$work/saved-distinfo"
rm "$pkg/patches/patch-zz-sunau-current-api"
sed '/SHA1 (patch-zz-sunau-current-api)/d' "$work/saved-distinfo" > "$pkg/distinfo"
negative omitted-adaptation
cp "$work/saved-patch" "$pkg/patches/patch-zz-sunau-current-api"
cp "$work/saved-distinfo" "$pkg/distinfo"
cp "$profile/sources.tsv" "$work/saved-manifest"
sed 's/8c385028/00000000/' "$work/saved-manifest" > "$profile/sources.tsv"
negative altered-source
cp "$work/saved-manifest" "$profile/sources.tsv"
pkg=$profile/recipes/audio/lame
cp "$pkg/distinfo" "$work/lame-distinfo"
mv "$pkg/patches/patch-zz-frontend-encoding" "$work/lame-patch"
sed '/SHA1 (patch-zz-frontend-encoding)/d' "$work/lame-distinfo" > "$pkg/distinfo"
negative omitted-lame-adaptation
mv "$work/lame-patch" "$pkg/patches/patch-zz-frontend-encoding"
cp "$work/lame-distinfo" "$pkg/distinfo"
sed 's/3df5124d/00000000/' "$work/saved-manifest" > "$profile/sources.tsv"
negative altered-lame-source
cp "$work/saved-manifest" "$profile/sources.tsv"
sh "$profile/validate.sh"

echo 'PASS: both media exports reject missing recipes, altered/omitted patches and incorrect source pins before creating a destination'
