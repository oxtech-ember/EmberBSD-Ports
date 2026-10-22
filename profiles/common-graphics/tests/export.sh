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
mkdir "$work/source/profiles/common-graphics"
cp -R "$root/profiles/common-graphics/." "$work/source/profiles/common-graphics/"
ln -s "$root/.git" "$work/source/.git"
ln -s "$root/upstream" "$work/source/upstream"
ln -s "$root/profiles/common-media" "$work/source/profiles/common-media"
mkdir "$work/source/profiles/common-build-tools"
cp -R "$root/profiles/common-build-tools/." "$work/source/profiles/common-build-tools/"
ln -s "$root/profiles/development-toolchain" "$work/source/profiles/development-toolchain"
ln -s "$root/probes" "$work/source/probes"
cp -R "$root/pkgsrc" "$work/source/pkgsrc"
script=$work/source/scripts/prepare-pkgsrc.sh
profile=$work/source/profiles/common-graphics
fmt_recipe=$profile/recipes/textproc/fmtlib
[ -f "$fmt_recipe/Makefile" ]
[ ! -e "$profile/recipes/devel/fmtlib" ]
grep -Fqx 'PKGNAME=	${DISTNAME:S/fmt/fmtlib/}' "$fmt_recipe/Makefile"
grep -Fqx 'BUILDLINK_PKGSRCDIR.fmtlib?=	../../textproc/fmtlib' "$fmt_recipe/buildlink3.mk"
[ "$(awk -F '\t' '$1 == "textproc/fmtlib" { count++ } END { print count + 0 }' "$profile/sources.tsv")" -eq 1 ]
printf 'PASS: fmtlib uses its pkgsrc textproc path and matching package name\n'
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
bsdtar=$work/source/profiles/common-build-tools/patches/pkgsrc-bsdtar-common-zlib.patch
mv "$bsdtar" "$work/bsdtar-zlib-patch"
negative missing-bsdtar-zlib-infrastructure
mv "$work/bsdtar-zlib-patch" "$bsdtar"
swig=$work/source/profiles/common-build-tools/recipes/devel/swig4
for name in Makefile PLIST patches/patch-CCache_ccache.c; do
    mv "$swig/$name" "$work/swig-input"
    negative "missing-swig-${name##*/}"
    mv "$work/swig-input" "$swig/$name"
done
cp "$swig/distinfo" "$work/swig-distinfo"
sed '/SHA1 (patch-CCache_ccache.c)/d' "$work/swig-distinfo" > "$swig/distinfo"
negative missing-swig-patch-checksum
mv "$work/swig-distinfo" "$swig/distinfo"
shared_pcre2=$profile/recipes/devel/pcre2/options.mk
mv "$shared_pcre2" "$work/pcre2-options.mk"
negative missing-shared-pcre2-options
mv "$work/pcre2-options.mk" "$shared_pcre2"
for name in cross.mk files/target-query.py files/sdk_source.py files/elf-needed.sh; do
    helper=$profile/recipes/devel/gobject-introspection/$name
    mv "$helper" "$work/gi-helper"
    negative "missing-gi-${name##*/}"
    mv "$work/gi-helper" "$helper"
done
cups_delta=$profile/cross/current-cups.patch
mv "$cups_delta" "$work/cups-delta"
negative missing-common-cups-delta
mv "$work/cups-delta" "$cups_delta"
gi=$profile/recipes/devel/gobject-introspection
cp "$gi/distinfo" "$work/gi-distinfo"
mv "$gi/patches/patch-girepository_gthash-memory" "$work/gi-gthash-patch"
negative missing-gi-gthash-patch
sed '/SHA1 (patch-girepository_gthash-memory)/d' "$work/gi-distinfo" > "$gi/distinfo"
negative omitted-gi-gthash-patch-and-checksum
mv "$work/gi-gthash-patch" "$gi/patches/patch-girepository_gthash-memory"
cp "$work/gi-distinfo" "$gi/distinfo"
printf '\nchanged\n' >> "$gi/patches/patch-girepository_gthash-memory"
negative altered-gi-gthash-patch
cp "$root/profiles/common-graphics/recipes/devel/gobject-introspection/patches/patch-girepository_gthash-memory" "$gi/patches/patch-girepository_gthash-memory"
mv "$gi/patches/patch-tests_scanner_test_ccompiler.py" "$work/gi-compiler-mock-patch"
negative missing-gi-compiler-mock-patch
sed '/SHA1 (patch-tests_scanner_test_ccompiler.py)/d' "$work/gi-distinfo" > "$gi/distinfo"
negative omitted-gi-compiler-mock-patch-and-checksum
mv "$work/gi-compiler-mock-patch" "$gi/patches/patch-tests_scanner_test_ccompiler.py"
cp "$work/gi-distinfo" "$gi/distinfo"
printf '\nchanged\n' >> "$gi/patches/patch-tests_scanner_test_ccompiler.py"
negative altered-gi-compiler-mock-patch
cp "$root/profiles/common-graphics/recipes/devel/gobject-introspection/patches/patch-tests_scanner_test_ccompiler.py" "$gi/patches/patch-tests_scanner_test_ccompiler.py"
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
helper=$profile/recipes/graphics/gdk-pixbuf2/files/target-tools.py
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
for name in PLIST.runtime files/select-package-stage.pl; do
    mv "$wayland/$name" "$work/wayland-split-helper"
    negative "missing-wayland-$(basename "$name")"
    mv "$work/wayland-split-helper" "$wayland/$name"
done
for name in Makefile buildlink3.mk DESCR PLIST; do
    mv "$profile/recipes/devel/wayland-devel/$name" "$work/wayland-sdk-helper"
    negative "missing-wayland-sdk-$name"
    mv "$work/wayland-sdk-helper" "$profile/recipes/devel/wayland-devel/$name"
done
consumer=$profile/recipes/devel/wayland-protocols/cross-scanner.mk
mv "$consumer" "$work/scanner-consumer.mk"
negative missing-scanner-consumer
mv "$work/scanner-consumer.mk" "$consumer"
cp "$profile/sources.tsv" "$work/saved-manifest"
sed 's/bce5f7fb/00000000/' "$work/saved-manifest" > "$profile/sources.tsv"
negative altered-manifest
cp "$work/saved-manifest" "$profile/sources.tsv"
for dependency in www/webkit-gtk41 www/webkit-gtk60 math/eigen3 textproc/rapidjson x11/xorgproto devel/libudev-bsd wayland/wlroots wayland/labwc wayland/sway wayland/swaylock devel/libevdev-chunk textproc/json-c x11/xkeyboard-config devel/input-headers x11/libxkbcommon sysutils/hwdata sysutils/seatd x11/libdisplay-info graphics/libliftoff devel/libopeninput devel/glib2 devel/libffi devel/pcre2 textproc/fmtlib x11/pixman graphics/cairo fonts/harfbuzz converters/fribidi graphics/png graphics/lerc graphics/openexr graphics/OpenJPH graphics/jbigkit graphics/freetype2 archivers/lzo x11/libXt x11/libspnav devel/pango devel/libsfdo sysutils/dbus devel/gobject-introspection graphics/librsvg multimedia/dav1d devel/xxhash graphics/gdk-pixbuf2 databases/shared-mime-info; do
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
for name in builtin.mk hacks.mk; do
    mv "$profile/recipes/x11/pixman/$name" "$work/pixman-$name"
    negative "missing-pixman-$name"
    mv "$work/pixman-$name" "$profile/recipes/x11/pixman/$name"
done
for dependency in devel/glib2-tools devel/glib2-introspection devel/gdbus-codegen; do
    mv "$profile/recipes/$dependency/Makefile" "$work/family-Makefile"
    negative "missing-${dependency##*/}-family-recipe"
    mv "$work/family-Makefile" "$profile/recipes/$dependency/Makefile"
done
for entry in 'textproc/rapidjson:patch-shared-pool-owner' 'textproc/rapidjson:patch-wide-stream' 'textproc/rapidjson:patch-float-oracle' 'textproc/rapidjson:patch-pointer-token-copy' 'textproc/rapidjson:patch-allocator-ownership' 'textproc/rapidjson:patch-system-gtest' 'textproc/rapidjson:patch-gtest-suite' 'x11/libspnav:patch-Makefile.in' 'x11/libspnav:patch-src_spnav.c' 'graphics/openexr:patch-test-tmpdir' 'graphics/openexr:patch-test-assertions' 'graphics/openexr:patch-cmake_OpenEXRSetup.cmake' 'www/webkit-gtk41:patch-Source_cmake_FindGI.cmake' 'www/webkit-gtk41:patch-Source_ThirdParty_skia_locale-l' 'graphics/lerc:patch-src_LercLib_fpl__EsriHuffman.cpp' 'graphics/jbigkit:patch-cli-cleanup' 'graphics/jbigkit:patch-test-cleanup' 'devel/libffi:patch-src_powerpc_ffi__powerpc.h' 'wayland/labwc:patch-docs_meson.build' 'wayland/labwc:patch-meson.build' 'wayland/labwc:patch-src_common_string-helpers.c' 'wayland/labwc:patch-src_cycle_osd-field.c' 'wayland/sway:patch-common_stringop.c' 'wayland/sway:patch-common_util.c' 'wayland/sway:patch-include_ipc.h' 'wayland/sway:patch-include_stringop.h' 'wayland/sway:patch-meson.build' 'wayland/sway:patch-sway_commands.c' 'wayland/sway:patch-sway_commands_move.c' 'wayland/sway:patch-sway_commands_rename.c' 'wayland/sway:patch-sway_commands_workspace.c' 'wayland/sway:patch-sway_input_input-manager.c' 'wayland/sway:patch-sway_input_seat.c' 'wayland/sway:patch-sway_ipc-json.c' 'wayland/sway:patch-sway_ipc-server.c' 'wayland/sway:patch-sway_ipc-startup.c' 'wayland/sway:patch-sway_tree_output.c' 'wayland/sway:patch-sway_tree_workspace.c' 'wayland/sway:patch-swaybar_i3bar.c' 'wayland/sway:patch-swaybar_tray_icon.c' 'wayland/swaylock:patch-loop.c' 'wayland/swaylock:patch-main.c' 'devel/libevdev-chunk:patch-libevdev.c' 'devel/libevdev-chunk:patch-libevdev_libevdev.h' 'textproc/json-c:patch-json_object.c' 'textproc/json-c:patch-tests_test_json_parse_cli.test' 'graphics/gdk-pixbuf2:patch-emberbsd_meson.build' 'graphics/gdk-pixbuf2:patch-emberbsd_gdk-pixbuf_meson.build' 'graphics/gdk-pixbuf2:patch-emberbsd_thumbnailer_meson.build' 'graphics/gdk-pixbuf2:patch-emberbsd_build-aux_gen-thumbnailer.py' 'databases/shared-mime-info:patch-src_update-mime-database.cpp' 'graphics/librsvg:patch-meson_gir-cross.build' 'graphics/librsvg:patch-rsvg_meson.build' 'graphics/librsvg:patch-gdk-pixbuf-loader_meson.build' 'graphics/librsvg:patch-.._vendor_wide-1.7.1_src_f32x4__.rs' 'devel/glib2:patch-meson.build' 'devel/glib2:patch-meson_gir-cross.build' 'devel/glib2:patch-girepository_compiler_meson.build' 'converters/fribidi:patch-bin_Makefile.in' 'archivers/lzo:patch-src_lzo1f__d.ch' 'x11/libXt:patch-util_Makefile.in'; do
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
delta=$ngspice/patches/patch-13-target-memory-query
mv "$delta" "$work/ngspice-patch-link"
negative missing-ngspice-patch
# Matching bytes at an unexpected link destination must still be refused.
ln -s "$root/probes/kicad/ngspice/patches/target-memory-query.patch" "$delta"
negative unexpected-ngspice-patch-origin
rm "$delta"
mv "$work/ngspice-patch-link" "$delta"
ln -s "$root/probes/kicad/ngspice/README.md" "$ngspice/unexpected-link"
negative unexpected-ngspice-extra-link
rm "$ngspice/unexpected-link"
cp "$ngspice/distinfo" "$work/ngspice-distinfo"
mv "$delta" "$work/ngspice-patch-link"
sed '/SHA1 (patch-13-target-memory-query)/d' "$work/ngspice-distinfo" > "$ngspice/distinfo"
negative omitted-ngspice-patch-and-checksum
mv "$work/ngspice-patch-link" "$delta"
cp "$work/ngspice-distinfo" "$ngspice/distinfo"
cp "$profile/sources.tsv" "$work/ngspice-sources"
sed '/^cad\/ng-spice[[:space:]]/d' "$work/ngspice-sources" > "$profile/sources.tsv"
negative omitted-ngspice-source-pin
cp "$work/ngspice-sources" "$profile/sources.tsv"
occt=$profile/recipes/cad/occt
mv "$occt/PLIST" "$work/occt-PLIST"
negative missing-occt-inventory
mv "$work/occt-PLIST" "$occt/PLIST"
delta=$occt/patches/patch-rwstl-alignment
mv "$delta" "$work/occt-patch-link"
negative missing-occt-stl-patch
ln -s "$root/probes/kicad/occt/patches/rwstl-alignment.patch" "$delta"
negative unexpected-occt-patch-origin
rm "$delta"
mv "$work/occt-patch-link" "$delta"
ln -s "$root/probes/kicad/occt/README.md" "$occt/unexpected-link"
negative unexpected-occt-extra-link
rm "$occt/unexpected-link"
cp "$occt/distinfo" "$work/occt-distinfo"
mv "$delta" "$work/occt-patch-link"
sed '/SHA1 (patch-rwstl-alignment)/d' "$work/occt-distinfo" > "$occt/distinfo"
negative omitted-occt-stl-patch-and-checksum
mv "$work/occt-patch-link" "$delta"
cp "$work/occt-distinfo" "$occt/distinfo"
cp "$profile/sources.tsv" "$work/occt-sources"
sed '/^cad\/occt[[:space:]]/d' "$work/occt-sources" > "$profile/sources.tsv"
negative omitted-occt-source-pin
cp "$work/occt-sources" "$profile/sources.tsv"
sed 's/6297cc55a1720523a437c54d07dc16b9da8c5f5ab5800da3c6ebded568d53c18/6297cc55a1720523a437c54d07dc16b9da8c5f5ab5800da3c6ebded568d53c19/' "$work/occt-sources" > "$profile/sources.tsv"
negative altered-occt-source-pin
cp "$work/occt-sources" "$profile/sources.tsv"
if sh "$script" "$work/unknown" unknown > "$work/unknown.log" 2>&1; then exit 1; fi
[ ! -e "$work/unknown" ]
kicad=$profile/recipes/cad/kicad10
kinng=$kicad/patches/patch-libs_kinng_src_kinng.cpp
mv "$kinng" "$work/kinng-patch"
negative missing-kinng-patch
cp "$kicad/distinfo" "$work/kicad-distinfo"
sed '/SHA1 (patch-libs_kinng_src_kinng.cpp)/d' "$work/kicad-distinfo" > "$kicad/distinfo"
negative omitted-kinng-patch-and-checksum
cp "$work/kicad-distinfo" "$kicad/distinfo"
cp "$work/kinng-patch" "$kinng"
printf '\nchanged\n' >> "$kinng"
negative changed-kinng-patch
mv "$work/kinng-patch" "$kinng"
nng=$profile/recipes/net/nng
for name in options.mk patches/patch-drain-before-free patches/patch-docs-required; do
    mv "$nng/$name" "$work/nng-input"
    negative "missing-nng-${name##*/}"
    mv "$work/nng-input" "$nng/$name"
done
delta=$nng/patches/patch-drain-before-free
mv "$delta" "$work/nng-patch-link"
ln -s "$root/probes/kicad/nng/patches/drain-before-free.patch" "$delta"
negative unexpected-nng-patch-origin
rm "$delta"
mv "$work/nng-patch-link" "$delta"
ln -s "$root/probes/kicad/nng/README.md" "$nng/unexpected-link"
negative unexpected-nng-extra-link
rm "$nng/unexpected-link"
cp "$profile/sources.tsv" "$work/nng-sources"
sed '/^net\/nng[[:space:]]/d' "$work/nng-sources" > "$profile/sources.tsv"
negative omitted-nng-source-pin
cp "$work/nng-sources" "$profile/sources.tsv"
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
            grep -Fqx 'CMAKE_CONFIGURE_ARGS+=	-DNNG_TOOLS:BOOL=ON' "$tree/net/nng/Makefile"
            [ "$(find "$tree/net/nng" -type l | wc -l | tr -d ' ')" = 0 ]
            diff -qr "$profile/recipes/x11/libspnav" "$tree/x11/libspnav"
            grep -Fqx 'CUPS_VERS=	2.4.20' "$tree/print/cups/Makefile.common"
            grep -Fqx 'CONFIGURE_ENV+=	KRB5CONFIG=${KRB5_CONFIG:Q}' "$tree/print/libcups/options.mk"
            cups_gss_patch=$tree/print/cups-base/patches/patch-config-scripts_cups-gssapi-target
            grep -Fqx "SHA1 (patch-config-scripts_cups-gssapi-target) = $(sed '/[$]NetBSD.*/d' "$cups_gss_patch" | shasum -a 1 | awk '{ print $1 }')" "$tree/print/cups-base/distinfo"
            diff -qr "$root/profiles/common-build-tools/recipes/devel/flex" "$tree/devel/flex"
            for recipe in net/nng graphics/MesaLib x11/libdrm devel/wayland devel/wayland-protocols x11/xorgproto devel/libudev-bsd wayland/wlroots wayland/labwc wayland/sway wayland/swaylock devel/libevdev-chunk textproc/json-c x11/xkeyboard-config devel/input-headers x11/libxkbcommon sysutils/hwdata sysutils/seatd x11/libdisplay-info graphics/libliftoff devel/libopeninput devel/glib2 devel/libffi devel/pcre2 textproc/fmtlib graphics/cairo fonts/harfbuzz converters/fribidi graphics/png graphics/openexr graphics/OpenJPH graphics/jbigkit graphics/freetype2 archivers/lzo x11/libXt devel/pango devel/libsfdo sysutils/dbus devel/gobject-introspection devel/glib2-tools devel/glib2-introspection devel/gdbus-codegen graphics/librsvg multimedia/dav1d devel/xxhash graphics/gdk-pixbuf2 databases/shared-mime-info www/webkit-gtk41 www/webkit-gtk60 math/eigen3 textproc/rapidjson cad/ng-spice cad/ng-spice-shared cad/kicad10 cad/occt; do diff -qr "$profile/recipes/$recipe" "$tree/$recipe"; done
            diff -qr "$profile/recipes/devel/wayland-devel" "$tree/devel/wayland-devel"
            cmp "$profile/mk.conf" "$tree/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
            cmp "$profile/sources.tsv" "$tree/EMBERBSD-COMMON-GRAPHICS-SOURCES" ;;
        *)
            cmp "$root/upstream/pkgsrc/print/cups/Makefile.common" "$tree/print/cups/Makefile.common"
            # BEGIN libspnav-absence-guard
            [ ! -e "$tree/x11/libspnav" ]
            [ ! -L "$tree/x11/libspnav" ]
            # END libspnav-absence-guard
            for recipe in net/nng graphics/MesaLib x11/libdrm devel/wayland devel/wayland-protocols x11/xorgproto devel/libudev-bsd wayland/wlroots wayland/labwc x11/xkeyboard-config devel/input-headers x11/libxkbcommon sysutils/hwdata sysutils/seatd x11/libdisplay-info graphics/libliftoff devel/libopeninput devel/glib2 devel/libffi textproc/fmtlib graphics/cairo fonts/harfbuzz converters/fribidi graphics/png graphics/openexr graphics/OpenJPH graphics/jbigkit graphics/freetype2 archivers/lzo x11/libXt devel/pango devel/libsfdo sysutils/dbus devel/gobject-introspection devel/glib2-tools devel/glib2-introspection devel/gdbus-codegen graphics/librsvg multimedia/dav1d devel/xxhash graphics/gdk-pixbuf2 databases/shared-mime-info www/webkit-gtk41 www/webkit-gtk60 math/eigen3 textproc/rapidjson cad/ng-spice cad/ng-spice-shared; do diff -qr "$root/upstream/pkgsrc/$recipe" "$tree/$recipe"; done
            [ ! -e "$tree/cad/kicad10" ]
            [ ! -e "$tree/devel/wayland-devel" ]
            [ ! -e "$tree/EMBERBSD-COMMON-GRAPHICS-MK.CONF" ] ;;
    esac
    case "$mode" in common-build-tools|common-graphics|common-media|plasma-mobile)
        diff -qr "$root/profiles/common-build-tools/recipes/devel/swig4" "$tree/devel/swig4"
        diff -qr "$root/profiles/common-graphics/recipes/devel/pcre2" "$tree/devel/pcre2"
        for recipe in lang/python315 lang/rust-bin lang/rust-std-aarch64-netbsd devel/meson lang/llvm lang/clang devel/lld devel/py-llvm-lit devel/binutils devel/py-mako textproc/py-markupsafe textproc/py-yaml; do diff -qr "$root/profiles/common-build-tools/recipes/$recipe" "$tree/$recipe"; done
        # Python 3.15 is the common overlay; the older upstream recipe stays intact.
        diff -qr "$root/upstream/pkgsrc/lang/python314" "$tree/lang/python314"
        cmp "$root/profiles/common-build-tools/mk.conf" "$tree/EMBERBSD-COMMON-TOOLS-MK.CONF" ;;
    *)
        diff -qr "$root/upstream/pkgsrc/devel/swig4" "$tree/devel/swig4"
        diff -qr "$root/upstream/pkgsrc/devel/pcre2" "$tree/devel/pcre2" ;;
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
