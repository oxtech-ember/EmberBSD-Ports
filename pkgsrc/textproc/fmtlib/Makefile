# $NetBSD: Makefile,v 1.1 2026/10/19 00:00:00 emberbsd Exp $

DISTNAME=	fmt-12.2.0
PKGNAME=	${DISTNAME:S/fmt/fmtlib/}
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=fmtlib/}
GITHUB_PROJECT=	fmt
GITHUB_TAG=	${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/fmtlib/fmt
COMMENT=	Formatting library for C++
LICENSE=	mit

USE_LANGUAGES=	c c++

CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_BINDIR=bin
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_INCLUDEDIR=include
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DFMT_DOC=OFF
CMAKE_CONFIGURE_ARGS+=	-DFMT_INSTALL=ON
CMAKE_CONFIGURE_ARGS+=	-DFMT_TEST=OFF

PKGCONFIG_OVERRIDE+=	support/cmake/fmt.pc.in

.include "../../mk/bsd.prefs.mk"
.include "../../mk/emberbsd-native-cxx-runtime.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 1
.endif

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
