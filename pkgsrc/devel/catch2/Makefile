# $NetBSD: Makefile,v 1.32 2026/09/03 05:07:13 adam Exp $

DISTNAME=	Catch2-3.16.0
PKGNAME=	${DISTNAME:tl}
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=catchorg/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	bsiegert@NetBSD.org
HOMEPAGE=	https://github.com/catchorg/Catch2
COMMENT=	C++ test framework for unit tests
LICENSE=	boost-license

WRKSRC=		${WRKDIR}/${DISTNAME}

USE_CXX_FEATURES=	c++17
USE_LANGUAGES=		c c++

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILD_DEFS+=	EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DPKGCONFIG_INSTALL_DIR:PATH=${PREFIX}/lib/pkgconfig
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_CXX_STANDARD=17

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
