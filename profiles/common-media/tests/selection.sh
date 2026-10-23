#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted actual full-recipe BSD make selection checks.
# The host boundary supplies target/installed-package metadata, not native tools.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
tree=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
make=${BMAKE:-bmake}
mkdir -p "$work/sys" "$work/base/include/GL" "$work/base/include/EGL" "$work/base/include/libdrm" "$work/base/lib/pkgconfig"
cat > "$work/sys/bsd.own.mk" <<'MK'
# Explicit host-only MAKECONF boundary; no native sysroot/tool acceptance.
.if exists(${MAKECONF})
.include "${MAKECONF}"
.endif
MK
cat > "$work/mk.conf" <<MK
.include "$tree/EMBERBSD-COMMON-TOOLS-MK.CONF"
.include "$tree/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
.include "$tree/EMBERBSD-COMMON-MEDIA-MK.CONF"
.if exists("$tree/EMBERBSD-PLASMA-TOOLKIT-MK.CONF")
.include "$tree/EMBERBSD-PLASMA-TOOLKIT-MK.CONF"
.endif
MK
# Plausible native graphics providers must still lose to actual package recipes.
printf '#define GL_VERSION_1_5 1\n' > "$work/base/include/GL/gl.h"
printf '#define GLX_VERSION_1_4 1\n' > "$work/base/include/GL/glx.h"
printf '#define EGL_DRM_MASTER_FD_EXT 0x333C\n' > "$work/base/include/EGL/eglext.h"
for pc in gl libdrm xrandr; do printf 'Name: %s\nVersion: 99.0.0\n' "$pc" > "$work/base/lib/pkgconfig/$pc.pc"; done
# Compile the exact pinned pkgtools version matcher with only header glue.
cp "$tree/pkgtools/pkg_install/files/lib/dewey.c" "$work/dewey.c"
cp "$tree/pkgtools/pkg_install/files/lib/dewey.h" "$work/dewey.h"
printf '#include <sys/types.h>\n' > "$work/nbcompat.h"
cat > "$work/defs.h" <<'C'
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <err.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
C
"${CC:-cc}" -DHAVE_CTYPE_H=1 -DHAVE_STDLIB_H=1 -I"$work" \
    "$work/dewey.c" "$(dirname -- "$0")/../../common-graphics/tests/pkg-admin-boundary.c" -o "$work/pkg-admin-boundary"
"$work/pkg-admin-boundary" pmatch 'test>=2.4.134nb1' test-2.4.134nb1
if "$work/pkg-admin-boundary" pmatch 'test>=2.4.134nb1' test-2.4.134; then exit 1; fi
run() {
    recipe=$1; shift
    "$make" -r -m "$work/sys" -C "$tree/$recipe" \
        MAKECONF="$work/mk.conf" OPSYS=NetBSD OS_VERSION=11.0 OPSYS_VERSION=110000 \
        NATIVE_OPSYS=NetBSD NATIVE_OS_VERSION=11.0 NATIVE_OPSYS_VERSION=110000 \
        LOWER_OPSYS=netbsd MACHINE_ARCH=aarch64 HOST_MACHINE_ARCH=aarch64 \
        MACHINE_GNU_ARCH=aarch64 MACHINE_CPU=aarch64 OBJECT_FMT=ELF \
        X11_TYPE=native X11BASE="$work/base" LOCALBASE=/usr/pkg PREFIX=/usr/pkg \
        CC=cc CXX=c++ _GCC_VERSION=16.2.0 PKG_INFO=/usr/bin/true PKG_ADMIN="$work/pkg-admin-boundary" \
        PKG_BUILD_OPTIONS.llvm=tests PKG_BUILD_OPTIONS.gcc16=c++ \
        PKG_BUILD_OPTIONS.MesaLib='llvm x11 wayland' \
        PKG_BUILD_OPTIONS.ffmpeg9='ass aom bluray freetype fontconfig gnutls lame libvpx libwebp opus speex theora vorbis x264 x265 xvid x11' \
        USE_BUILTIN.pthread=yes H_PTHREAD=/usr/include/pthread.h "$@"
}
for recipe in multimedia/ffmpeg9 multimedia/ffplay9 multimedia/qt6-qtmultimedia sysutils/kf6-kfilemetadata; do
    run "$recipe" show-depends > "$work/${recipe##*/}-depends.txt" 2>&1
    for variable in PKGNAME PKG_FAIL_REASON PKG_OPTIONS CONFIGURE_ARGS; do
        run "$recipe" show-var VARNAME="$variable" > "$work/${recipe##*/}-$variable.txt" 2>&1
    done
    if grep -E 'ffmpeg[0-8][>:]|media dependency|FFmpeg 9 package integration is pending|common media profile|common FFmpeg 9 media profile' "$work/${recipe##*/}"-*.txt; then exit 1; fi
done
# Take the expected versions from the canonical recipes, not from this test.
recipe_version() {
    distname=$(run "$1" show-var VARNAME=DISTNAME)
    revision=$(run "$1" show-var VARNAME=PKGREVISION)
    printf '%s%s\n' "${distname##*-}" "${revision:+nb$revision}"
}
ffmpeg=$(recipe_version multimedia/ffmpeg9)
grep -x "ffmpeg9-$ffmpeg" "$work/ffmpeg9-PKGNAME.txt"
grep -F -- '--enable-sdl2' "$work/ffplay9-CONFIGURE_ARGS.txt" >/dev/null
grep -F -- '--enable-ffplay' "$work/ffplay9-CONFIGURE_ARGS.txt" >/dev/null
for recipe in ffplay9 qt6-qtmultimedia kf6-kfilemetadata; do
    grep -F 'ffmpeg9>=9.0.2:../../multimedia/ffmpeg9' "$work/$recipe-depends.txt"
done
for option in ass aom bluray freetype fontconfig gnutls lame libvpx libwebp opus speex theora vorbis x264 x265 xvid x11; do
    grep -w "$option" "$work/ffmpeg9-PKG_OPTIONS.txt" >/dev/null
done
for arg in --enable-avfilter --enable-gpl --enable-shared --enable-libxml2 --enable-libharfbuzz --enable-zlib --enable-bzlib --enable-lzma --disable-autodetect; do
    grep -F -- "$arg" "$work/ffmpeg9-CONFIGURE_ARGS.txt" >/dev/null
done
if grep -E -- '--disable-(everything|network|protocols|decoders|encoders|demuxers|muxers)' "$work/ffmpeg9-CONFIGURE_ARGS.txt"; then exit 1; fi
for pair in 'DISTNAME=ffmpeg-9.0.1' 'BUILDLINK_PKGSRCDIR.ffmpeg9=../../multimedia/ffmpeg8' 'BUILDLINK_API_DEPENDS.ffmpeg9=ffmpeg9>=9.0.0' 'CONFIGURE_ARGS=--disable-everything'; do
    run multimedia/ffmpeg9 show-var VARNAME=PKG_FAIL_REASON "$pair" > "$work/override-$(printf '%s' "$pair" | tr '/=' '--').log"
done
grep "requires the FFmpeg ${ffmpeg%nb*} recipe" "$work/override-DISTNAME-ffmpeg-9.0.1.log"
grep 'unprepared FFmpeg provider' "$work/override-BUILDLINK_PKGSRCDIR.ffmpeg9-..-..-multimedia-ffmpeg8.log"
grep 'overridden FFmpeg requirements' "$work/override-BUILDLINK_API_DEPENDS.ffmpeg9-ffmpeg9>-9.0.0.log"
grep 'Select FFmpeg features through package options' "$work/override-CONFIGURE_ARGS---disable-everything.log"
run multimedia/ffmpeg8 show-var VARNAME=PKG_FAIL_REASON > "$work/old-provider.log"
grep 'requires FFmpeg 9; migrate this consumer' "$work/old-provider.log"
echo 'PASS: full recipe selection, both consumers, default codecs and provider/configuration failures; native package checks remain required'
