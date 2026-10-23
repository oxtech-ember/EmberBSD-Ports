# $NetBSD: Makefile,v 1.1 2026/04/13 15:49:39 kikadf Exp $

DISTNAME=	seatd-0.9.3
PKGREVISION=	1
CATEGORIES=	sysutils
MASTER_SITES=	${MASTER_SITE_GITHUB:=kennylevinsen/}

MAINTAINER=	kikadf@NetBSD.org
HOMEPAGE=	https://git.sr.ht/~kennylevinsen/seatd/
COMMENT=	Seat management daemon and library
LICENSE=	mit

USE_TOOLS+=	pkg-config

PKGCONFIG_OVERRIDE_STAGE=	pre-install
PKGCONFIG_OVERRIDE+=		output/meson-private/libseat.pc

MESON_ARGS+=	--wrap-mode=nofallback
MESON_ARGS+=	-Dlibseat-logind=disabled
MESON_ARGS+=	-Dlibseat-builtin=enabled

SPECIAL_PERMS+=	bin/seatd-launch ${SETUID_ROOT_PERMS}

BUILDLINK_TRANSFORM+=	rm:-Werror

.include "../../devel/meson/build.mk"
TOOL_DEPENDS+=	scdoc>=1.11.5:../../textproc/scdoc
EMBERBSD_NATIVE_GRAPHICS_PC= scdoc:1.11.5
.include "../../sysutils/hwdata/native-meson.mk"
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
.include "../../textproc/scdoc/tool.mk"
.endif
.include "../../mk/bsd.pkg.mk"
