# $NetBSD$
# Origin: TeamHypersomnia/rectpack2D current master snapshot 7dde22ed (2026-08-10).
DISTNAME=	rectpack2d-0.0.20260810
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=TeamHypersomnia/}
GITHUB_PROJECT=	rectpack2D
GITHUB_TAG=	7dde22ed7a707b952b9f8fb263bf3c94f4cef898
WRKSRC=		${WRKDIR}/rectpack2D-${GITHUB_TAG}
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/TeamHypersomnia/rectpack2D/
COMMENT=	Header-only C++ rectangle packing library
LICENSE=	mit
USE_LANGUAGES=	c++
USE_CXX_FEATURES=	c++17
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DRECTPACK2D_BUILD_EXAMPLE=OFF
INSTALLATION_DIRS+=	share/licenses/rectpack2d
post-extract:
	${MKDIR} ${WRKSRC}/cmake
	${CP} ${FILESDIR}/rectpack2dConfig.cmake.in ${WRKSRC}/cmake/rectpack2dConfig.cmake.in
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/rectpack2d/LICENSE
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
