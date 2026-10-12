#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), full polkit cross-recipe regression.
set -eu
[ "$#" = 3 ] || { echo 'Usage: polkit-source.sh DISTFILES PREPARED_PKGSRC NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set cross MAKECONF}" "${DIGEST:?Set native digest}"
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
distfiles=$(CDPATH= cd -- "$1" && pwd)
prepared=$(CDPATH= cd -- "$2" && pwd)
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
mkdir "$work/pkgsrc" "$work/source"
git -C "$root/upstream/pkgsrc" archive --format=tar HEAD security/polkit security/polkit-qt6 > "$work/recipes.tar"
tar -xf "$work/recipes.tar" -C "$work/pkgsrc"
patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$root/probes/plasma-mobile/toolkit/current-polkit.patch"
for file in Makefile distinfo patches/patch-meson-cross.build; do
    cmp "$work/pkgsrc/security/polkit/$file" "$prepared/security/polkit/$file"
done
for file in Makefile distinfo buildlink3.mk PLIST; do
    cmp "$work/pkgsrc/security/polkit-qt6/$file" "$prepared/security/polkit-qt6/$file"
done
verifier=$root/upstream/pkgsrc/mk/checksum/checksum.awk
export DIGEST
(cd "$distfiles" && awk -f "$verifier" -- "$work/pkgsrc/security/polkit/distinfo" polkit-127.tar.gz)
(cd "$distfiles" && awk -f "$verifier" -- "$work/pkgsrc/security/polkit-qt6/distinfo" polkit-qt-1-0.201.1.tar.xz)
tar -xf "$distfiles/polkit-127.tar.gz" --strip-components=1 -C "$work/source"
for patch_name in $(awk '/^SHA1 \(patch-/ { gsub(/[()]/,"",$2); print $2 }' "$work/pkgsrc/security/polkit/distinfo"); do
    awk -f "$verifier" -- -p "$work/pkgsrc/security/polkit/distinfo" "$work/pkgsrc/security/polkit/patches/$patch_name"
    patch -f -N -F 0 -p0 -d "$work/source" < "$work/pkgsrc/security/polkit/patches/$patch_name"
done
if patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$root/probes/plasma-mobile/toolkit/current-polkit.patch" > "$work/repeated.log" 2>&1; then exit 1; fi
recipe=$prepared/security/polkit
"$BMAKE" -C "$recipe" -V '${MESON_BINARIES}' > "$work/cross-tools.txt"
for tool in glib-mkenums glib-genmarshal gdbus-codegen g-ir-scanner g-ir-compiler; do
    grep -q "$tool" "$work/cross-tools.txt"
    executable=$("$BMAKE" -C "$recipe" -V "\${MESON_BINARY.$tool}")
    [ -x "$executable" ]
done
[ -z "$("$BMAKE" -C "$recipe" USE_CROSS_COMPILE=no -V '${MESON_BINARIES}')" ]
"$BMAKE" -C "$recipe" -V '${MESON_ARGS}' > "$work/options.txt"
! grep -Eq 'introspection=(false|disabled)|libs-only=true' "$work/options.txt"
rm "$work/recipes.tar"
echo 'PASS: full polkit source patches, native generators, unchanged native selection and retained introspection/daemon'
