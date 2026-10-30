#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted package patch/archive integration checks.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 VERIFIED_DISTFILES NEW_WORK" >&2; exit 2; }
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
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
    pkg=$profile/../../pkgsrc/$recipe
    verify_archive "$distfiles/$archive"
    # A headers-only package and its runtime may share one upstream archive.
    # Each recipe still needs its own independently patched source view.
    tree=$work/$recipe
    mkdir -p "$tree"
    tar -xf "$distfiles/$archive" --strip-components=1 -C "$tree"
    for name in $(awk '/^SHA1 \(patch-/ {gsub(/[()]/,"",$2); print $2}' "$pkg/distinfo"); do
        actual=$(sed '/[$]NetBSD.*/d' "$pkg/patches/$name" | shasum -a 1 | awk '{print $1}')
        expected=$(awk -v n="($name)" '$1=="SHA1" && $2==n {print $4}' "$pkg/distinfo")
        [ "$actual" = "$expected" ]
        patch -f -N -F 0 -p0 -d "$tree" < "$pkg/patches/$name"
    done
    printf '%s\t%s\n' "$recipe" "$sha" >> "$work/verified.tsv"
done < "$profile/sources.tsv"
# Mutate only the small libdrm archive and execute the exact positive verifier.
awk -F '\t' '$1=="x11/libdrm"' "$profile/sources.tsv" > "$work/negative-source.tsv"
IFS="$(printf '\t')" read -r recipe archive sha url < "$work/negative-source.tsv"
pkg=$profile/../../pkgsrc/$recipe
cp "$distfiles/$archive" "$work/altered-$archive"
printf x >> "$work/altered-$archive"
if verify_archive "$work/altered-$archive" > "$work/archive-negative.log" 2>&1; then exit 1; fi
# Failed extraction must retain failure.
printf 'not an xz archive\n' > "$work/corrupt.tar.xz"
if tar -xf "$work/corrupt.tar.xz" -C "$work" > "$work/extraction-negative.log" 2>&1; then exit 1; fi
if patch -f -N -F 0 -p0 -d "$work/graphics/MesaLib" < "$profile/../../pkgsrc/graphics/MesaLib/patches/patch-meson-python-selection" > "$work/repeated.log" 2>&1; then exit 1; fi
# Accepted probe source deltas remain byte-identical; do not repeat their contracts.
root=$(CDPATH= cd -- "$profile/../.." && pwd)
for name in patch-dso-lifetime patch-src_util_half__float.c patch-bin_symbols-check.py patch-include_c99__alloca.h; do
    cmp "$root/probes/wayland-utm/patches/mesa/$name" "$profile/../../pkgsrc/graphics/MesaLib/patches/$name"
done
for file in "$root"/probes/wayland-utm/patches/libdrm/patch-*; do
    cmp "$file" "$profile/../../pkgsrc/x11/libdrm/patches/${file##*/}"
done
echo 'PASS: original archives, filtered package hashes, once-only zero-fuzz patching, extraction failure and exact accepted patch identity'
