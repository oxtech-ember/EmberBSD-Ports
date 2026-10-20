#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Reproduce the security and network recipe deltas.
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
patch -f -N -F 0 -p1 -d "$work/pkgsrc" < \
    "$root/profiles/common-build-tools/patches/pkgsrc-curl-security.patch"
patch -f -N -F 0 -p1 -d "$work/pkgsrc" < \
    "$root/profiles/common-graphics/cross/gsettings-desktop-schemas-cross-gir.patch"
patch -f -N -d "$work/pkgsrc" -p1 -F 0 < \
    "$root/profiles/common-graphics/cross/libproxy-cross-disable-introspection.patch"
for delta in libproxy-cross current-network-deps; do
    patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$toolkit/$delta.patch"
done
# The curl cross Makefile delta is owned by the common profile.
cross_patch=$root/profiles/common-build-tools/patches/pkgsrc-cross-packages.patch
awk '/^--- a\/www\/curl\/Makefile$/ { copying=1 } \
    copying && /^--- a\// && $0 != "--- a/www/curl/Makefile" { exit } copying { print }' \
    "$cross_patch" > "$work/curl-cross.patch"
[ -s "$work/curl-cross.patch" ]
patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$work/curl-cross.patch"
cmp "$work/pkgsrc/www/curl/Makefile" "$prepared/www/curl/Makefile"
cmp "$work/pkgsrc/www/curl/Makefile.common" "$prepared/www/curl/Makefile.common"
cmp "$work/pkgsrc/www/curl/distinfo" "$prepared/www/curl/distinfo"
cmp "$work/pkgsrc/www/curl/options.mk" "$prepared/www/curl/options.mk"
grep -Eq '^PKG_SUGGESTED_OPTIONS=[[:space:]]*http2 inet6 idn$' \
    "$prepared/www/curl/options.mk"
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
www/curl curl-8.23.0.tar.xz
www/libproxy libproxy-0.5.12.tar.gz
DEPS
cmp "$work/pkgsrc/www/libproxy/options.mk" "$prepared/www/libproxy/options.mk"
if patch -f -N -F 0 -p0 -d "$work/source/libproxy" \
    < "$work/pkgsrc/www/libproxy/patches/patch-src_libproxy_meson.build-cross" \
    > "$work/repeated.log" 2>&1; then exit 1; fi
rm "$work/recipes.tar"
echo 'PASS: curl security and network recipe deltas, exact prepared files, archive/patch hashes and zero-fuzz source patches'
