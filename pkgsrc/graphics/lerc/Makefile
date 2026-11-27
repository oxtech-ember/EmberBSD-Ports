# $NetBSD: Makefile,v 1.4 2026/07/27 14:42:21 wiz Exp $

DISTNAME=	lerc-4.3.0
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_GITHUB:=Esri/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	bsiegert@NetBSD.org
HOMEPAGE=	https://github.com/Esri/lerc
COMMENT=	Limited Error Raster Compression library
LICENSE=	apache-2.0

USE_TOOLS+=	pkg-config
USE_LANGUAGES=	c c++

.include "../../mk/bsd.prefs.mk"

# Preserve source locations in assert diagnostics without recording the build directory.
.if ${OPSYS} == "NetBSD" && (!empty(PKGSRC_COMPILER:Mclang) || !empty(PKGSRC_COMPILER:Mgcc))
PKGREVISION=	1
CXXFLAGS+=	-fmacro-prefix-map=${WRKSRC}=.
.endif

PKGCONFIG_OVERRIDE+=	Lerc.pc.in

.include "../../devel/cmake/build.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	2	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"
