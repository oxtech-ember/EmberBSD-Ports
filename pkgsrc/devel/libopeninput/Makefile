# $NetBSD: Makefile,v 1.2 2026/05/27 17:14:19 kikadf Exp $

.include "Makefile.common"

PKGREVISION=	1
COMMENT=	Wscons(4) and kqueue(2) based port of libinput

USE_TOOLS+=	pkg-config
UDEV_REQUIRED=	yes

# wscons
ONLY_FOR_PLATFORM=	NetBSD-*-*
ONLY_FOR_PLATFORM+=	OpenBSD-*-*

MESON_ARGS+=	--wrap-mode=nofallback
MESON_ARGS+=	-Ddebug-gui=false
MESON_ARGS+=	-Dlua-plugins=disabled
MESON_ARGS+=	-Dlibwacom=false
MESON_ARGS+=	-Ddocumentation=false
MESON_ARGS+=	-Dtests=false
# Upstream's default derives a build-host path from the target prefix.
# Its explicit search root must be the pkgsrc dependency view on both hosts.
MESON_ARGS+=	-Depoll-dir=${BUILDLINK_DIR}

PKGCONFIG_OVERRIDE+=		output/meson-private/libinput.pc
PKGCONFIG_OVERRIDE_STAGE=	post-build

.include "../../devel/meson/build.mk"
.include "../../devel/libepoll-shim/buildlink3.mk"
BUILDLINK_API_DEPENDS.input-headers+= input-headers>=1.31.3
.include "../../devel/input-headers/buildlink3.mk"
.include "../../mk/udev.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
