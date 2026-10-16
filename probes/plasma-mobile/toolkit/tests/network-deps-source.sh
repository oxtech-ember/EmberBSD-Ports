#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Reproduce the networking recipe/source deltas.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 DISTFILES PREPARED_PKGSRC NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
toolkit=$root/probes/plasma-mobile/toolkit
distfiles=$(CDPATH= cd -- "$1" && pwd)
prepared=$(CDPATH= cd -- "$2" && pwd)
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
mkdir "$work/pkgsrc" "$work/source"
git -C "$root/upstream/pkgsrc" archive --format=tar HEAD \
    devel/libidn2 sysutils/gsettings-desktop-schemas www/libproxy www/curl > "$work/recipes.tar"
tar -xf "$work/recipes.tar" -C "$work/pkgsrc"
for delta in libproxy-cross current-network-deps; do
    patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$toolkit/$delta.patch"
done
# The curl Makefile delta is owned by the common cross profile.
awk '/^--- a\/www\/curl\/Makefile$/ { copying=1 } copying { print }' \
    "$root/profiles/common-build-tools/patches/pkgsrc-cross-packages.patch" > "$work/curl.patch"
[ -s "$work/curl.patch" ]
patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$work/curl.patch"
cmp "$work/pkgsrc/www/curl/Makefile" "$prepared/www/curl/Makefile"
verifier=$root/upstream/pkgsrc/mk/checksum/checksum.awk
export DIGEST=${DIGEST:-digest}
while read -r recipe archive; do
    pkg=$work/pkgsrc/$recipe
    for file in Makefile PLIST distinfo; do cmp "$pkg/$file" "$prepared/$recipe/$file"; done
    (cd "$distfiles" && awk -f "$verifier" -- "$pkg/distinfo" "$archive")
    mkdir "$work/source/${recipe##*/}"
    tar -xf "$distfiles/$archive" --strip-components=1 -C "$work/source/${recipe##*/}"
    for name in $(awk '/^SHA1 \(patch-/ { gsub(/[()]/,"",$2); print $2 }' "$pkg/distinfo"); do
        cmp "$pkg/patches/$name" "$prepared/$recipe/patches/$name"
        awk -f "$verifier" -- -p "$pkg/distinfo" "$pkg/patches/$name"
        patch -f -N -F 0 -p0 -d "$work/source/${recipe##*/}" < "$pkg/patches/$name"
    done
done <<'DEPS'
devel/libidn2 libidn2-2.3.8.tar.gz
sysutils/gsettings-desktop-schemas gsettings-desktop-schemas-51.0.tar.xz
www/libproxy libproxy-0.5.12.tar.gz
DEPS
cmp "$work/pkgsrc/www/libproxy/options.mk" "$prepared/www/libproxy/options.mk"
if patch -f -N -F 0 -p0 -d "$work/source/libproxy" \
    < "$work/pkgsrc/www/libproxy/patches/patch-src_libproxy_meson.build-cross" \
    > "$work/repeated.log" 2>&1; then exit 1; fi
rm "$work/recipes.tar"
echo 'PASS: pinned recipe deltas, exact prepared files, archive/patch hashes and zero-fuzz source patches'
