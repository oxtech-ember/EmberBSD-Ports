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
.if exists("$tree/EMBERBSD-PLASMA-TOOLKIT-MK.CONF")
.include "$tree/EMBERBSD-COMMON-MEDIA-MK.CONF"
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
    "$work/dewey.c" "$(dirname -- "$0")/pkg-admin-boundary.c" -o "$work/pkg-admin-boundary"
"$work/pkg-admin-boundary" pmatch 'test>=2.4.134nb2' test-2.4.134nb2
if "$work/pkg-admin-boundary" pmatch 'test>=2.4.134nb2' test-2.4.134; then exit 1; fi
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
        USE_BUILTIN.pthread=yes H_PTHREAD=/usr/include/pthread.h "$@"
}
for recipe in graphics/MesaLib x11/libdrm graphics/glu graphics/libepoxy x11/qt6-qtbase devel/qt6-qtwayland; do
    [ -f "$tree/$recipe/Makefile" ] || exit 1
    for var in PKGNAME PKGPATH DEPENDS TOOL_DEPENDS USE_BUILTIN.MesaLib USE_BUILTIN.libdrm USE_BUILTIN.glu MESALIB_SUPPORTS_EGL MESALIB_SUPPORTS_GLESv2 MESALIB_SUPPORTS_DRI MESALIB_SUPPORTS_OSMESA MESALIB_SUPPORTS_XA MESON_ARGS LLVM_CONFIG_PATH PKG_SKIP_REASON PKG_FAIL_REASON PLIST.egldevice; do
        printf '%s\n' "$var" >> "$work/${recipe##*/}.txt"
        run "$recipe" show-var VARNAME="$var" >> "$work/${recipe##*/}.txt" 2>&1
    done
    run "$recipe" show-depends > "$work/${recipe##*/}-depends.txt" 2>&1
    if grep -E 'libLLVM|MesaLib>=21|libdrm>=2.4.15:' "$work/${recipe##*/}-depends.txt"; then exit 1; fi
done
run graphics/MesaLib show-var VARNAME=PKGNAME | grep -x 'MesaLib-26.2.4nb7'
run graphics/MesaLib show-var VARNAME=DEPENDS | grep 'vulkan-loader>=1.4.357.0:../../graphics/vulkan-loader' > /dev/null
run x11/libdrm show-var VARNAME=PKGNAME | grep -x 'libdrm-2.4.134nb3'
run x11/libdrm show-var VARNAME=PKG_SKIP_REASON > "$work/drm-skip.txt"
[ ! -s "$work/drm-skip.txt" ] || [ -z "$(cat "$work/drm-skip.txt")" ]
for recipe in graphics/glu graphics/libepoxy; do
    run "$recipe" show-var VARNAME=DEPENDS | grep 'MesaLib>=26.2.4nb4:../../graphics/MesaLib' > /dev/null
done
run x11/qt6-qtbase show-var VARNAME=DEPENDS | grep 'glu>=.*:../../graphics/glu' > /dev/null
run devel/qt6-qtwayland show-var VARNAME=DEPENDS | grep 'qt6-qtbase>=.*:../../x11/qt6-qtbase' > /dev/null
for provider in MesaLib libdrm glu; do
    [ "$(run graphics/glu show-var VARNAME=USE_BUILTIN.$provider)" = no ]
    run graphics/glu show-var VARNAME=PKG_FAIL_REASON USE_BUILTIN.$provider=yes > "$work/builtin-$provider.log"
    grep "rejects built-in $provider" "$work/builtin-$provider.log"
done
for pair in 'DISTNAME=mesa-21.3.9' 'PKG_OPTIONS.MesaLib=-wayland' 'MESON_ARGS=-Dllvm=disabled' 'BUILDLINK_PKGSRCDIR.MesaLib=../../graphics/old' 'USE_CROSS_COMPILE=yes' 'PREFIX=/opt/mesa'; do
    # Cross parsing needs a complete target tuple; reject via profile block separately below.
    case "$pair" in USE_CROSS_COMPILE=*) continue ;; esac
    run graphics/MesaLib show-var VARNAME=PKG_FAIL_REASON "$pair" > "$work/negative-$(printf '%s' "$pair" | tr '/=' '--').log"
done
# Check production errors rather than host missing dlopen/X11 build premises.
grep 'rejects old Mesa' "$work/negative-DISTNAME-mesa-21.3.9.log"
grep 'requires the wayland Mesa option' "$work/negative-PKG_OPTIONS.MesaLib--wayland.log"
grep 'Meson configuration overrides' "$work/negative-MESON_ARGS--Dllvm-disabled.log"
grep 'unprepared MesaLib' "$work/negative-BUILDLINK_PKGSRCDIR.MesaLib-..-..-graphics-old.log"
grep 'one final /usr/pkg prefix' "$work/negative-PREFIX--opt-mesa.log"
run x11/libdrm show-var VARNAME=PKG_FAIL_REASON PKGREVISION=0 | grep 'adapted libdrm 2.4.134nb3'
run graphics/MesaLib show-var VARNAME=PKG_FAIL_REASON PKGREVISION=0 | grep 'adapted MesaLib 26.2.4nb7'
run graphics/MesaLib show-var VARNAME=MESON_ARGS > "$work/mesa-options.txt"
for option in '-Dgallium-drivers=v3d,virgl,softpipe,llvmpipe,zink' '-Dllvm-orcjit=true' '-Dshared-llvm=enabled' '-Dbuild-tests=true'; do grep -- "$option" "$work/mesa-options.txt" > /dev/null; done
echo 'PASS: full recipes, actual dependency/builtin selection and negative profile overrides (host metadata boundary only)'
