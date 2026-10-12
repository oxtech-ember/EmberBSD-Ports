#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Validate source metadata before creating a pkgsrc export.
set -eu
profile=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
pkg=$profile/recipes/multimedia/ffmpeg9
expected='multimedia/ffmpeg9 ffmpeg-9.0.2.tar.xz 8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz'
actual=$(awk '$1=="multimedia/ffmpeg9" { if (NF != 4) exit 1; print $1, $2, $3, $4 }' "$profile/sources.tsv")
[ "$actual" = "$expected" ] || { echo 'Incorrect common media source pin.' >&2; exit 2; }
for file in Makefile Makefile.common DESCR ALTERNATIVES PLIST distinfo options.mk buildlink3.mk; do
    [ -f "$pkg/$file" ] || { echo "Incomplete FFmpeg recipe: $file" >&2; exit 2; }
done
required=$(awk '/^SHA1 \(patch-/ {gsub(/[()]/,"",$2); print $2}' "$pkg/distinfo")
[ "$(printf '%s\n' "$required" | wc -l | tr -d ' ')" = 17 ] || {
    echo 'Incomplete FFmpeg patch manifest.' >&2; exit 2;
}
[ "$(find "$pkg/patches" -type f -name 'patch-*' | wc -l | tr -d ' ')" = 17 ] || {
    echo 'FFmpeg patch inventory differs.' >&2; exit 2;
}
for name in $required; do
    expected=$(awk -v n="($name)" '$1=="SHA1" && $2==n {print $4}' "$pkg/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$pkg/patches/$name" | shasum -a 1 | awk '{print $1}')
    [ "$actual" = "$expected" ] || { echo "FFmpeg patch checksum differs: $name" >&2; exit 2; }
done

# LAME is an MP3 dependency of the same FFmpeg provider, not a reduced probe.
expected='audio/lame lame-4.0.tar.gz 3df5124d5ad3a98312ffd7ba6a9b36230e4f8a3e66d3ce0f425e336c32d216eb https://downloads.sourceforge.net/project/lame/lame/4.0/lame-4.0.tar.gz'
actual=$(awk '$1=="audio/lame" { if (NF != 4) exit 1; print $1, $2, $3, $4 }' "$profile/sources.tsv")
[ "$actual" = "$expected" ] || { echo 'Incorrect LAME source pin.' >&2; exit 2; }
pkg=$profile/recipes/audio/lame
for file in Makefile DESCR PLIST distinfo options.mk buildlink3.mk patches/patch-zz-frontend-encoding; do
    [ -f "$pkg/$file" ] || { echo "Incomplete LAME recipe: $file" >&2; exit 2; }
done
[ "$(awk '/^SHA1 \(patch-/ {n++} END {print n}' "$pkg/distinfo")" = 4 ] || {
    echo 'Incomplete LAME patch manifest.' >&2; exit 2;
}
[ "$(find "$pkg/patches" -type f -name 'patch-*' | wc -l | tr -d ' ')" = 4 ] || {
    echo 'LAME patch inventory differs.' >&2; exit 2;
}

# All source entries own complete recipes and every source patch is checksummed.
awk -F '\t' '!/^#/ && NF { if (NF != 4 || $1 !~ /^[a-z0-9][a-z0-9-]*\/[a-z0-9][a-z0-9+-]*$/ || $2 !~ /^[a-zA-Z0-9][a-zA-Z0-9._+-]*\.tar\.(xz|gz)$/ || $4 !~ /^https:\/\// || seen[$1]++ || length($3) != 64 || $3 !~ /^[0-9a-f]+$/) exit 1; count++ } END { if (count != 11) exit 1 }' "$profile/sources.tsv"
while IFS="$(printf '\t')" read -r recipe archive sha url; do
    case "$recipe" in ''|'#'*) continue ;; esac
    pkg=$profile/recipes/$recipe
    case "$recipe" in
        multimedia/ffmpeg9|audio/lame) ;;
        *)
            case "$archive" in *-1.28.8.tar.xz) ;; *) echo "Wrong GStreamer family version: $recipe" >&2; exit 2 ;; esac
            [ "$(awk '$1 == "GST_VERSION=" {print $2}' "$profile/recipes/multimedia/gstreamer1/version.mk")" = 1.28.8 ] || exit 2
            ;;
    esac
    for algorithm in BLAKE2s SHA512 Size; do
        awk -v a="$algorithm" -v n="($archive)" '$1==a && $2==n {found=1} END {exit !found}' "$pkg/distinfo" || {
            echo "Missing source digest: $recipe/$archive/$algorithm" >&2; exit 2;
        }
    done
    for file in Makefile PLIST distinfo; do
        [ -f "$pkg/$file" ] || { echo "Incomplete media recipe: $recipe/$file" >&2; exit 2; }
    done
    for name in $(awk '/^SHA1 \(patch-/ {gsub(/[()]/,"",$2); print $2}' "$pkg/distinfo"); do
        expected=$(awk -v n="($name)" '$1=="SHA1" && $2==n {print $4}' "$pkg/distinfo")
        actual=$(sed '/[$]NetBSD.*/d' "$pkg/patches/$name" | shasum -a 1 | awk '{print $1}')
        [ "$actual" = "$expected" ] || { echo "Media patch checksum differs: $recipe/$name" >&2; exit 2; }
    done
done < "$profile/sources.tsv"
