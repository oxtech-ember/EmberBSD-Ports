#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted FFmpeg archive, patch and source PLIST checks.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 VERIFIED_DISTFILES NEW_WORK" >&2; exit 2; }
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
recipes=$(CDPATH= cd -- "$profile/../../pkgsrc" && pwd -P)
sh "$profile/validate.sh"
distfiles=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
verify_archive() {
    source_archive=$1
    [ "$(shasum -a 256 "$source_archive" | awk '{ print $1 }')" = "$sha" ] || return 1
    for algorithm in BLAKE2s SHA512; do
        expected=$(awk -v a="$algorithm" -v n="($archive)" '$1==a && $2==n {print $4}' "$pkg/distinfo")
        case "$algorithm" in
            BLAKE2s) actual=$("${OPENSSL:-openssl}" dgst -blake2s256 "$source_archive" | awk '{print $NF}') ;;
            SHA512) actual=$(shasum -a 512 "$source_archive" | awk '{print $1}') ;;
        esac
        [ "$actual" = "$expected" ] || return 1
    done
    [ "$(wc -c < "$source_archive" | tr -d ' ')" = "$(awk -v n="($archive)" '$1=="Size" && $2==n {print $4}' "$pkg/distinfo")" ] || return 1
}
while IFS="$(printf '\t')" read -r recipe archive sha url; do
    case "$recipe" in ''|'#'*) continue ;; esac
    pkg=$recipes/$recipe
    verify_archive "$distfiles/$archive"
    tree=$work/${archive%.tar.*}
    mkdir "$tree"
    tar -xf "$distfiles/$archive" --strip-components=1 -C "$tree"
    case "$recipe" in multimedia/x265) tree=$tree/source ;; esac
    for name in $(awk '/^SHA1 \(patch-/ {gsub(/[()]/,"",$2); print $2}' "$pkg/distinfo" | LC_ALL=C sort); do
        actual=$(sed '/[$]NetBSD.*/d' "$pkg/patches/$name" | shasum -a 1 | awk '{print $1}')
        expected=$(awk -v n="($name)" '$1=="SHA1" && $2==n {print $4}' "$pkg/distinfo")
        [ "$actual" = "$expected" ]
        patch -f -N -F 0 -p0 -d "$tree" < "$pkg/patches/$name"
    done
    printf '%s\t%s\n' "$recipe" "$sha" >> "$work/verified.tsv"
done < "$profile/sources.tsv"
awk '!/^#/ && NF' "$profile/sources.tsv" > "$work/source.tsv"
IFS="$(printf '\t')" read -r recipe archive sha url < "$work/source.tsv"
pkg=$recipes/$recipe
tree=$work/${archive%.tar.*}
# Exercise the same verifier with altered source data.
cp "$distfiles/$archive" "$work/altered-$archive"
printf x >> "$work/altered-$archive"
if verify_archive "$work/altered-$archive" > "$work/altered.log" 2>&1; then exit 1; fi
if patch -f -N -F 0 -p0 -d "$tree" < "$pkg/patches/patch-zz-sunau-current-api" > "$work/repeated.log" 2>&1; then exit 1; fi
ruby "$profile/tests/plist.rb" "$tree" "$pkg/PLIST" "$pkg/ALTERNATIVES"
echo 'PASS: all original media archives and patch hashes, zero-fuzz application; FFmpeg source-derived PLIST'
