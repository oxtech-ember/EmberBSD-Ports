#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted common dependency selection regression.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: $0 NEW_WORK" >&2; exit 2; }
toolkit=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
cp "$toolkit/mk.conf" "$work/toolkit.mk"
cp "$toolkit/../../../profiles/common-graphics/mk.conf" "$work/graphics.mk"
cp "$toolkit/../../../profiles/common-graphics/sources.tsv" "$work/EMBERBSD-COMMON-GRAPHICS-SOURCES"
cp "$toolkit/../../../profiles/common-media/mk.conf" "$work/media.mk"
cp "$toolkit/../../../profiles/common-media/sources.tsv" "$work/EMBERBSD-COMMON-MEDIA-SOURCES"
printf '# source-check common-tools marker\n' > "$work/EMBERBSD-COMMON-TOOLS-MK.CONF"
make=${BMAKE:-bmake}
cat > "$work/Makefile" <<'MAKE'
BSD_PKG_MK= yes
.include "graphics.mk"
.include "media.mk"
.include "toolkit.mk"
all:
	@if test -n '${PKG_FAIL_REASON:U}'; then printf '%s\n' '${PKG_FAIL_REASON}'; exit 1; fi
MAKE
for recipe in multimedia/ffmpeg multimedia/ffmpeg3 multimedia/ffmpeg8 multimedia/ffplay8; do
    if (cd "$work" && "$make" -r -m / OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=aarch64 PREFIX=/usr/pkg LOCALBASE=/usr/pkg EMBERBSD_COMMON_TOOLS=yes PKGPATH="$recipe") > "$work/${recipe##*/}.log" 2>&1; then
        echo "Unprepared old media dependency accepted: $recipe" >&2; exit 1
    fi
    grep -q 'requires FFmpeg 9; migrate this consumer' "$work/${recipe##*/}.log"
done
if (cd "$work" && "$make" -r -m / OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=aarch64 PREFIX=/usr/pkg LOCALBASE=/usr/pkg EMBERBSD_COMMON_TOOLS=yes PKGPATH=graphics/MesaLib DISTNAME=mesa-21.3.9) > "$work/mesa-old.log" 2>&1; then exit 1; fi
grep -q 'rejects old Mesa recipes' "$work/mesa-old.log"
if (cd "$work" && "$make" -r -m / OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=aarch64 PREFIX=/usr/pkg LOCALBASE=/usr/pkg PKGPATH=x11/qt6-qtbase) > "$work/missing-common.log" 2>&1; then exit 1; fi
grep -q 'requires the common build-tools profile' "$work/missing-common.log"
(cd "$work" && "$make" -r -m / OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=aarch64 PREFIX=/usr/pkg LOCALBASE=/usr/pkg EMBERBSD_COMMON_TOOLS=yes PKGPATH=x11/qt6-qtbase)
for variable in BUILDLINK_API_DEPENDS.MesaLib BUILDLINK_ABI_DEPENDS.MesaLib; do
    value=$(cd "$work" && "$make" -r -m / OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=aarch64 PREFIX=/usr/pkg LOCALBASE=/usr/pkg EMBERBSD_COMMON_TOOLS=yes PKGPATH=x11/qt6-qtbase -V "$variable")
    [ "$(printf '%s\n' "$value" | tr ' ' '\n' | sort -u)" = "$(printf '%s\n' 'MesaLib>=26.2.4' 'MesaLib>=26.2.4nb4')" ]
done
for variable in USE_BUILTIN.MesaLib USE_BUILTIN.glu USE_BUILTIN.libdrm; do
    value=$(cd "$work" && "$make" -r -m / OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=aarch64 PREFIX=/usr/pkg LOCALBASE=/usr/pkg EMBERBSD_COMMON_TOOLS=yes PKGPATH=x11/qt6-qtbase -V "$variable")
    [ "$value" = no ]
done
for recipe in multimedia/qt6-qtmultimedia sysutils/kf6-kfilemetadata multimedia/ffmpeg9; do
    (cd "$work" && "$make" -r -m / OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=aarch64 PREFIX=/usr/pkg LOCALBASE=/usr/pkg EMBERBSD_COMMON_TOOLS=yes PKGPATH="$recipe" DISTNAME=ffmpeg-9.0.2)
done
if (cd "$work" && "$make" -r -m / OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=aarch64 PREFIX=/usr/pkg LOCALBASE=/usr/pkg EMBERBSD_COMMON_TOOLS=yes EMBERBSD_COMMON_MEDIA=no PKGPATH=multimedia/qt6-qtmultimedia) > "$work/missing-media.log" 2>&1; then exit 1; fi
grep -q 'requires the common FFmpeg 9 media profile' "$work/missing-media.log"
echo 'PASS: common media required, old FFmpeg rejected, migrated consumers accepted and Mesa/libdrm selection retained'
# Native tool recursion must preserve the host compiler and job count. The
# old target-only profiles rejected this before xmlstarlet could build.
"$make" -C "$work" -r -m / OPSYS=Darwin OS_VERSION=27.0 MACHINE_ARCH=arm64 \
    PREFIX=/host LOCALBASE=/host EMBERBSD_COMMON_GRAPHICS_CROSS=yes \
    USE_CROSS_COMPILE=no PKGPATH=textproc/xmlstarlet \
    PKGSRC_COMPILER=clang MAKE_JOBS=4 > "$work/host-recursion.log" 2>&1
for pair in PKGSRC_COMPILER:clang MAKE_JOBS:4; do
    value=$("$make" -C "$work" -r -m / OPSYS=Darwin OS_VERSION=27.0 MACHINE_ARCH=arm64 \
        PREFIX=/host LOCALBASE=/host EMBERBSD_COMMON_GRAPHICS_CROSS=yes \
        USE_CROSS_COMPILE=no PKGPATH=textproc/xmlstarlet \
        PKGSRC_COMPILER=clang MAKE_JOBS=4 -V "${pair%:*}")
    [ "$value" = "${pair#*:}" ]
done
echo 'PASS: native tool recursion preserves host settings without target dependency policy'
