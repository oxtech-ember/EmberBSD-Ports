# $NetBSD: Makefile,v 1.5 2026/01/10 17:39:35 bsiegert Exp $

DISTNAME=	libdisplay-info-0.4.0
CATEGORIES=	x11
MASTER_SITES=	https://gitlab.freedesktop.org/emersion/libdisplay-info/-/releases/${PKGVERSION_NOREV}/downloads/
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	bsiegert@NetBSD.org
HOMEPAGE=	https://emersion.pages.freedesktop.org/libdisplay-info
COMMENT=	EDID and DisplayID library
LICENSE=	mit

USE_TOOLS+=	pkg-config
PYTHON_FOR_BUILD_ONLY=	tool
PYTHON_VERSION_REQD=	315
MESON_ARGS+=	--wrap-mode=nofallback
TOOL_DEPENDS+=	hwdata>=0.412:../../sysutils/hwdata
EMBERBSD_NATIVE_GRAPHICS_PC= hwdata:0.412
SUBST_CLASSES+=	python
SUBST_STAGE.python=	pre-configure
SUBST_FILES.python=	meson.build
SUBST_SED.python=	-e 's|@PYTHONBIN@|${TOOL_PYTHONBIN}|g'

BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,--version-script
BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,${WRKSRC}/libdisplay-info.map

.include "../../devel/meson/build.mk"
.include "../../sysutils/hwdata/native-meson.mk"
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
