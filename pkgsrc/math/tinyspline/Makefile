# $NetBSD$
# Origin: EmberBSD contributors; upstream msteinbeck/tinyspline v0.6.0.
DISTNAME=	tinyspline-0.6.0
PKGREVISION=	1
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=msteinbeck/}
GITHUB_TAG=	v${PKGVERSION_NOREV}
WRKSRC=		${WRKDIR}/tinyspline-0.6.0
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/msteinbeck/tinyspline/
COMMENT=	C and C++ library for spline interpolation and queries
LICENSE=	mit
USE_LANGUAGES=	c c++
USE_CXX_FEATURES=	c++11
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+=	-DTINYSPLINE_INSTALL_LIBRARY_DIR=lib
CMAKE_CONFIGURE_ARGS+=	-DTINYSPLINE_ENABLE_CXX=ON
CMAKE_CONFIGURE_ARGS+=	-DTINYSPLINE_ENABLE_ALL_INTERFACES=OFF
CMAKE_CONFIGURE_ARGS+=	-DTINYSPLINE_BUILD_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DTINYSPLINE_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DTINYSPLINE_BUILD_DOCS=OFF
INSTALLATION_DIRS+=	share/doc/tinyspline
post-extract:
	${MV} ${WRKSRC}/src/parson.h ${WRKSRC}/src/parson.h.bundled
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/doc/tinyspline/LICENSE
.include "../../textproc/parson/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
