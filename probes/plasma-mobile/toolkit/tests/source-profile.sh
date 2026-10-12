#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted Qt/KF source and exporter regression.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 VERIFIED_DISTFILES NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
toolkit=$root/probes/plasma-mobile/toolkit
distfiles=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
case "$work:$distfiles" in *[!a-zA-Z0-9_./:-]*) echo 'Use paths without shell metacharacters.' >&2; exit 2 ;; esac
cat > "$work/digest" <<'DIGEST'
#!/bin/sh
set -eu
algorithm=$1
shift
if [ "$#" -eq 0 ]; then
    [ "$algorithm" = SHA1 ] || exit 2
    shasum -a 1 | awk '{ print $1 }'
    exit
fi
for file do
    case "$algorithm" in
        SHA512) hash=$(shasum -a 512 "$file" | awk '{ print $1 }') ;;
        BLAKE2s) hash=$("${OPENSSL:-openssl}" dgst -blake2s256 "$file" | awk '{ print $NF }') ;;
        *) exit 2 ;;
    esac
    printf '%s (%s) = %s\n' "$algorithm" "$file" "$hash"
done
DIGEST
chmod +x "$work/digest"
export DIGEST=$work/digest
verifier=$root/upstream/pkgsrc/mk/checksum/checksum.awk
mkdir "$work/source"
while IFS="$(printf '\t')" read -r recipe archive sha url; do
    case "$recipe" in ''|'#'*) continue ;; esac
    pkg=$toolkit/recipes/$recipe
    [ "$(shasum -a 256 "$distfiles/$archive" | awk '{ print $1 }')" = "$sha" ]
    (cd "$distfiles" && awk -f "$verifier" -- "$pkg/distinfo" "$archive")
    recorded=$(awk -v name="($archive)" '$1 == "Size" && $2 == name { print $4 }' "$pkg/distinfo")
    [ "$(wc -c < "$distfiles/$archive" | tr -d ' ')" = "$recorded" ]
    required=$(awk '/^SHA1 \(patch-/ { gsub(/[()]/, "", $2); print $2 }' "$pkg/distinfo")
    actual=$(find "$pkg" -type f -name 'patch-*' | wc -l | tr -d ' ')
    expected=$(printf '%s\n' "$required" | awk 'NF { n++ } END { print n+0 }')
    [ "$actual" = "$expected" ] || { echo "Patch manifest differs: $recipe" >&2; exit 1; }
    if [ "$expected" -gt 0 ]; then
        tree=$work/source/${archive%.tar.xz}
        mkdir "$tree"
        tar -xf "$distfiles/$archive" --strip-components=1 -C "$tree"
        for name in $required; do
            [ -f "$pkg/patches/$name" ]
            awk -f "$verifier" -- -p "$pkg/distinfo" "$pkg/patches/$name"
            patch -f -N -F 0 -p0 -d "$tree" < "$pkg/patches/$name"
        done
    fi
    printf '%s\t%s\n' "$recipe" "$sha" >> "$work/verified.tsv"
done < "$toolkit/sources.tsv"
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
while IFS="$(printf '\t')" read -r recipe archive sha url; do
    case "$recipe" in ''|'#'*) continue ;; esac
    diff -qr "$toolkit/recipes/$recipe" "$work/pkgsrc/$recipe"
done < "$toolkit/sources.tsv"
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
