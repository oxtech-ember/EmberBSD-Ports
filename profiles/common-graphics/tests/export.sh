#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted canonical export and failure checks.
set -eu
preflight_only=no
if [ "${1:-}" = --preflight-only ]; then preflight_only=yes; shift; fi
[ "$#" -eq 1 ] || { echo "Usage: $0 [--preflight-only] NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
# Disposable source view shares read-only Git metadata; it never stages/commits.
mkdir -p "$work/source/scripts" "$work/source/profiles" "$work/tmp" "$work/bin"
cp "$root/scripts/prepare-pkgsrc.sh" "$work/source/scripts/"
cp -R "$root/profiles/common-graphics" "$work/source/profiles/"
ln -s "$root/.git" "$work/source/.git"
ln -s "$root/upstream" "$work/source/upstream"
ln -s "$root/profiles/common-media" "$work/source/profiles/common-media"
cp -R "$root/profiles/common-build-tools" "$work/source/profiles/common-build-tools"
ln -s "$root/profiles/development-toolchain" "$work/source/profiles/development-toolchain"
ln -s "$root/probes" "$work/source/probes"
cp -R "$root/pkgsrc" "$work/source/pkgsrc"
script=$work/source/scripts/prepare-pkgsrc.sh
profile=$work/source/profiles/common-graphics
negative_count=0
negative() {
    if sh "$script" "$work/rejected" common-graphics > "$work/$1.log" 2>&1; then exit 1; fi
    [ ! -e "$work/rejected" ]
    negative_count=$((negative_count + 1))
    printf 'PASS: preflight refusal %s\n' "$1"
}
std=$work/source/profiles/common-build-tools/recipes/lang/rust-std-aarch64-netbsd
mv "$std/Makefile" "$work/std-Makefile"
negative missing-rust-target-recipe
mv "$work/std-Makefile" "$std/Makefile"
mv "$std/patches/patch-stage0-cross-std" "$work/std-patch"
negative missing-rust-target-patch
mv "$work/std-patch" "$std/patches/patch-stage0-cross-std"
macho=$work/source/profiles/common-build-tools/patches/pkgsrc-macho-load-commands.patch
mv "$macho" "$work/macho-patch"
negative missing-macho-infrastructure
mv "$work/macho-patch" "$macho"
for name in cross.mk files/target-query.rb files/elf-needed.sh; do
    helper=$profile/recipes/devel/gobject-introspection/$name
    mv "$helper" "$work/gi-helper"
    negative "missing-gi-${name##*/}"
    mv "$work/gi-helper" "$helper"
done
for name in cross.mk cargo-depends.mk; do
    helper=$profile/recipes/graphics/librsvg/$name
    mv "$helper" "$work/librsvg-helper"
    negative "missing-librsvg-$name"
    mv "$work/librsvg-helper" "$helper"
done
for name in options.mk files/startlabwc.sh.in; do
    helper=$profile/recipes/wayland/labwc/$name
    mv "$helper" "$work/labwc-helper"
    negative "missing-labwc-${name##*/}"
    mv "$work/labwc-helper" "$helper"
done
helper=$profile/recipes/graphics/gdk-pixbuf2/files/target-tools.rb
mv "$helper" "$work/gdk-target-helper"
negative missing-gdk-target-helper
mv "$work/gdk-target-helper" "$helper"
pkg=$profile/recipes/graphics/MesaLib
mv "$pkg/Makefile" "$pkg/Makefile.saved"
negative missing-recipe
mv "$pkg/Makefile.saved" "$pkg/Makefile"
patch=$pkg/patches/patch-meson-python-selection
mv "$patch" "$work/saved-patch"
negative missing-patch
cp "$work/saved-patch" "$patch"
printf '\nchanged\n' >> "$patch"
negative altered-patch
cp "$work/saved-patch" "$patch"
# Omitting both a patch and its checksum must also fail before destination creation.
cp "$pkg/distinfo" "$work/saved-distinfo"
mv "$pkg/patches/patch-dso-lifetime" "$work/saved-lifetime"
sed '/SHA1 (patch-dso-lifetime)/d' "$work/saved-distinfo" > "$pkg/distinfo"
negative omitted-accepted-patch
mv "$work/saved-lifetime" "$pkg/patches/patch-dso-lifetime"
cp "$work/saved-distinfo" "$pkg/distinfo"
wayland=$profile/recipes/devel/wayland
cp "$wayland/distinfo" "$work/wayland-distinfo"
for name in patch-tests_client-test.c patch-tests_test-helpers.c; do
    mv "$wayland/patches/$name" "$work/$name"
    sed "/SHA1 ($name)/d" "$work/wayland-distinfo" > "$wayland/distinfo"
    negative "omitted-$name"
    mv "$work/$name" "$wayland/patches/$name"
    cp "$work/wayland-distinfo" "$wayland/distinfo"
done
consumer=$profile/recipes/devel/wayland-protocols/cross-scanner.mk
mv "$consumer" "$work/scanner-consumer.mk"
negative missing-scanner-consumer
mv "$work/scanner-consumer.mk" "$consumer"
cp "$profile/sources.tsv" "$work/saved-manifest"
sed 's/bce5f7fb/00000000/' "$work/saved-manifest" > "$profile/sources.tsv"
negative altered-manifest
cp "$work/saved-manifest" "$profile/sources.tsv"
for dependency in math/eigen3 x11/xorgproto devel/libudev-bsd wayland/wlroots wayland/labwc x11/xkeyboard-config devel/input-headers x11/libxkbcommon sysutils/hwdata sysutils/seatd x11/libdisplay-info graphics/libliftoff devel/libopeninput devel/glib2 devel/libffi devel/pcre2 graphics/cairo fonts/harfbuzz converters/fribidi graphics/png graphics/freetype2 archivers/lzo x11/libXt devel/pango devel/libsfdo sysutils/dbus devel/gobject-introspection graphics/librsvg multimedia/dav1d devel/xxhash graphics/gdk-pixbuf2 databases/shared-mime-info; do
    # Every added consumer/dependency needs its exact source pin.
    awk -F '\t' -v dep="$dependency" 'BEGIN { OFS="\t" }
        $1 == dep { $3="0000000000000000000000000000000000000000000000000000000000000000" }
        { print }' "$work/saved-manifest" > "$profile/sources.tsv"
    negative "altered-${dependency##*/}-pin"
    cp "$work/saved-manifest" "$profile/sources.tsv"
    mv "$profile/recipes/$dependency/Makefile" "$work/dependency-Makefile"
    negative "missing-${dependency##*/}-recipe"
    mv "$work/dependency-Makefile" "$profile/recipes/$dependency/Makefile"
done
for dependency in devel/glib2-tools devel/glib2-introspection devel/gdbus-codegen; do
    mv "$profile/recipes/$dependency/Makefile" "$work/family-Makefile"
    negative "missing-${dependency##*/}-family-recipe"
    mv "$work/family-Makefile" "$profile/recipes/$dependency/Makefile"
done
for entry in 'devel/libffi:patch-src_powerpc_ffi__powerpc.h' 'wayland/labwc:patch-docs_meson.build' 'wayland/labwc:patch-meson.build' 'wayland/labwc:patch-src_common_string-helpers.c' 'wayland/labwc:patch-src_cycle_osd-field.c' 'graphics/gdk-pixbuf2:patch-emberbsd_meson.build' 'graphics/gdk-pixbuf2:patch-emberbsd_gdk-pixbuf_meson.build' 'graphics/gdk-pixbuf2:patch-emberbsd_thumbnailer_meson.build' 'graphics/gdk-pixbuf2:patch-emberbsd_build-aux_gen-thumbnailer.py' 'databases/shared-mime-info:patch-src_update-mime-database.cpp' 'graphics/librsvg:patch-meson_gir-cross.build' 'graphics/librsvg:patch-rsvg_meson.build' 'graphics/librsvg:patch-gdk-pixbuf-loader_meson.build' 'graphics/librsvg:patch-.._vendor_wide-1.7.1_src_f32x4__.rs' 'devel/glib2:patch-meson.build' 'devel/glib2:patch-meson_gir-cross.build' 'devel/glib2:patch-girepository_compiler_meson.build' 'converters/fribidi:patch-bin_Makefile.in' 'archivers/lzo:patch-src_lzo1f__d.ch' 'x11/libXt:patch-util_Makefile.in'; do
    dependency=${entry%:*}
    name=${entry#*:}
    cp "$profile/recipes/$dependency/distinfo" "$work/new-dependency-distinfo"
    mv "$profile/recipes/$dependency/patches/$name" "$work/new-dependency-patch"
    sed "/SHA1 ($name)/d" "$work/new-dependency-distinfo" > "$profile/recipes/$dependency/distinfo"
    negative "omitted-$name"
    mv "$work/new-dependency-patch" "$profile/recipes/$dependency/patches/$name"
    cp "$work/new-dependency-distinfo" "$profile/recipes/$dependency/distinfo"
done
helper=$profile/recipes/sysutils/hwdata/native-meson.mk
mv "$helper" "$work/native-meson.mk"
negative missing-native-graphics-guard
mv "$work/native-meson.mk" "$helper"
for entry in 'sysutils/seatd:patch-wscons-keyboard-restore' 'devel/libopeninput:patch-wscons-absolute-pointer'; do
    dependency=${entry%:*}
    name=${entry#*:}
    cp "$profile/recipes/$dependency/distinfo" "$work/input-distinfo"
    mv "$profile/recipes/$dependency/patches/$name" "$work/input-patch"
    sed "/SHA1 ($name)/d" "$work/input-distinfo" > "$profile/recipes/$dependency/distinfo"
    negative "omitted-$name"
    mv "$work/input-patch" "$profile/recipes/$dependency/patches/$name"
    cp "$work/input-distinfo" "$profile/recipes/$dependency/distinfo"
done
xkb=$profile/recipes/x11/libxkbcommon
cp "$xkb/distinfo" "$work/xkb-distinfo"
mv "$xkb/patches/patch-meson-legacy-root" "$work/xkb-legacy-root"
sed '/SHA1 (patch-meson-legacy-root)/d' "$work/xkb-distinfo" > "$xkb/distinfo"
negative omitted-xkb-runtime-patch
mv "$work/xkb-legacy-root" "$xkb/patches/patch-meson-legacy-root"
cp "$work/xkb-distinfo" "$xkb/distinfo"
wlroots=$profile/recipes/wayland/wlroots
cp "$wlroots/distinfo" "$work/wlroots-distinfo"
mv "$wlroots/patches/patch-software-primary-node" "$work/wlroots-software-node"
sed '/SHA1 (patch-software-primary-node)/d' "$work/wlroots-distinfo" > "$wlroots/distinfo"
negative omitted-wlroots-software-node-patch
mv "$work/wlroots-software-node" "$wlroots/patches/patch-software-primary-node"
cp "$work/wlroots-distinfo" "$wlroots/distinfo"
ngspice=$profile/recipes/cad/ng-spice
shared=$profile/recipes/cad/ng-spice-shared
mv "$shared/Makefile" "$work/ngspice-shared-Makefile"
negative missing-ngspice-shared-recipe
mv "$work/ngspice-shared-Makefile" "$shared/Makefile"
delta=$ngspice/patches/patch-12-shared-command-cleanup
mv "$delta" "$work/ngspice-patch-link"
negative missing-ngspice-patch
# Matching bytes at an unexpected link destination must still be refused.
ln -s "$root/probes/kicad/ngspice/patches/shared-command-cleanup.patch" "$delta"
negative unexpected-ngspice-patch-origin
rm "$delta"
mv "$work/ngspice-patch-link" "$delta"
ln -s "$root/probes/kicad/ngspice/README.md" "$ngspice/unexpected-link"
negative unexpected-ngspice-extra-link
rm "$ngspice/unexpected-link"
cp "$ngspice/distinfo" "$work/ngspice-distinfo"
mv "$delta" "$work/ngspice-patch-link"
sed '/SHA1 (patch-12-shared-command-cleanup)/d' "$work/ngspice-distinfo" > "$ngspice/distinfo"
negative omitted-ngspice-patch-and-checksum
mv "$work/ngspice-patch-link" "$delta"
cp "$work/ngspice-distinfo" "$ngspice/distinfo"
cp "$profile/sources.tsv" "$work/ngspice-sources"
sed '/^cad\/ng-spice[[:space:]]/d' "$work/ngspice-sources" > "$profile/sources.tsv"
negative omitted-ngspice-source-pin
cp "$work/ngspice-sources" "$profile/sources.tsv"
if sh "$script" "$work/unknown" unknown > "$work/unknown.log" 2>&1; then exit 1; fi
[ ! -e "$work/unknown" ]
negative_count=$((negative_count + 1))
printf 'PASS: preflight refusal unknown-mode\n'
if [ "$preflight_only" = yes ]; then
    printf 'PASS: %s preflight refusal checks; full export/composition was not run\n' "$negative_count"
    exit 0
fi
# Failure after archive creation must preserve its status and clean the tempfile.
REAL_CP=$(command -v cp); export REAL_CP
cat > "$work/bin/cp" <<'SH'
#!/bin/sh
for arg do
    if [ "$arg" = "${GRAPHICS_FAIL_SOURCE:-}" ]; then exit 42; fi
done
exec "$REAL_CP" "$@"
SH
chmod +x "$work/bin/cp"
status=0
PATH="$work/bin:$PATH" TMPDIR="$work/tmp" GRAPHICS_FAIL_SOURCE="$pkg" \
    sh "$script" "$work/failed-export" common-graphics > "$work/failed-export.log" 2>&1 || status=$?
[ "$status" -eq 42 ]
[ -z "$(find "$work/tmp" -name 'ember-pkgsrc.*')" ]
# Only completed disposable source exports are removed; logs remain.
rm -rf "$work/failed-export"
for mode in default development-toolchain common-build-tools common-graphics common-media plasma-mobile; do
    tree=$work/export
    if [ "$mode" = default ]; then sh "$script" "$tree" > "$work/$mode.log" 2>&1
    else sh "$script" "$tree" "$mode" > "$work/$mode.log" 2>&1; fi
    case "$mode" in
        common-graphics|common-media|plasma-mobile)
            for recipe in graphics/MesaLib x11/libdrm devel/wayland devel/wayland-protocols x11/xorgproto devel/libudev-bsd wayland/wlroots wayland/labwc x11/xkeyboard-config devel/input-headers x11/libxkbcommon sysutils/hwdata sysutils/seatd x11/libdisplay-info graphics/libliftoff devel/libopeninput devel/glib2 devel/libffi devel/pcre2 graphics/cairo fonts/harfbuzz converters/fribidi graphics/png graphics/freetype2 archivers/lzo x11/libXt devel/pango devel/libsfdo sysutils/dbus devel/gobject-introspection devel/glib2-tools devel/glib2-introspection devel/gdbus-codegen graphics/librsvg multimedia/dav1d devel/xxhash graphics/gdk-pixbuf2 databases/shared-mime-info math/eigen3 cad/ng-spice cad/ng-spice-shared; do diff -qr "$profile/recipes/$recipe" "$tree/$recipe"; done
            cmp "$profile/mk.conf" "$tree/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
            cmp "$profile/sources.tsv" "$tree/EMBERBSD-COMMON-GRAPHICS-SOURCES" ;;
        *)
            for recipe in graphics/MesaLib x11/libdrm devel/wayland devel/wayland-protocols x11/xorgproto devel/libudev-bsd wayland/wlroots wayland/labwc x11/xkeyboard-config devel/input-headers x11/libxkbcommon sysutils/hwdata sysutils/seatd x11/libdisplay-info graphics/libliftoff devel/libopeninput devel/glib2 devel/libffi devel/pcre2 graphics/cairo fonts/harfbuzz converters/fribidi graphics/png graphics/freetype2 archivers/lzo x11/libXt devel/pango devel/libsfdo sysutils/dbus devel/gobject-introspection devel/glib2-tools devel/glib2-introspection devel/gdbus-codegen graphics/librsvg multimedia/dav1d devel/xxhash graphics/gdk-pixbuf2 databases/shared-mime-info math/eigen3 cad/ng-spice cad/ng-spice-shared; do diff -qr "$root/upstream/pkgsrc/$recipe" "$tree/$recipe"; done
            [ ! -e "$tree/EMBERBSD-COMMON-GRAPHICS-MK.CONF" ] ;;
    esac
    case "$mode" in common-build-tools|common-graphics|common-media|plasma-mobile)
        for recipe in lang/python314 lang/python315 lang/rust-bin lang/rust-std-aarch64-netbsd devel/meson lang/llvm lang/clang devel/lld devel/py-llvm-lit devel/binutils devel/py-mako textproc/py-markupsafe textproc/py-yaml; do diff -qr "$root/profiles/common-build-tools/recipes/$recipe" "$tree/$recipe"; done
        cmp "$root/profiles/common-build-tools/mk.conf" "$tree/EMBERBSD-COMMON-TOOLS-MK.CONF" ;;
    esac
    case "$mode" in development-toolchain|common-build-tools|common-graphics|common-media|plasma-mobile)
        cmp "$root/profiles/development-toolchain/mk.conf" "$tree/EMBERBSD-DEVELOPMENT-MK.CONF" ;;
    esac
    case "$mode" in
        common-media|plasma-mobile)
            diff -qr "$root/profiles/common-media/recipes/multimedia/ffmpeg9" "$tree/multimedia/ffmpeg9"
            cmp "$root/profiles/common-media/mk.conf" "$tree/EMBERBSD-COMMON-MEDIA-MK.CONF" ;;
        *) diff -qr "$root/upstream/pkgsrc/multimedia/ffmpeg9" "$tree/multimedia/ffmpeg9"; [ ! -e "$tree/EMBERBSD-COMMON-MEDIA-MK.CONF" ] ;;
    esac
    if [ "$mode" = plasma-mobile ]; then

        while IFS="$(printf '\t')" read -r recipe archive sha url; do
            case "$recipe" in ''|'#'*) continue ;; esac
            diff -qr "$root/probes/plasma-mobile/toolkit/recipes/$recipe" "$tree/$recipe"
        done < "$root/probes/plasma-mobile/toolkit/sources.tsv"
        cmp "$root/probes/plasma-mobile/toolkit/mk.conf" "$tree/EMBERBSD-PLASMA-TOOLKIT-MK.CONF"
    fi
    if sh "$script" "$tree" > "$work/existing-$mode.log" 2>&1; then exit 1; fi
    printf '%s: exact composition passed\n' "$mode" >> "$work/composition.txt"
    rm -rf "$tree"
done
# The old namespace collision refusal remains active even in the new profile.
mkdir "$work/source/pkgsrc/graphics"
if sh "$script" "$work/collision" common-graphics > "$work/collision.log" 2>&1; then exit 1; fi
grep 'Upstream already has graphics' "$work/collision.log"
rm -rf "$work/collision"
echo 'PASS: canonical composition, preserved sibling modes and the composed media profile, preflight failures, namespace collision and tempfile cleanup'
