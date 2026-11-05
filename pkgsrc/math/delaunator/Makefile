# $NetBSD$
# Origin: abellgithub/delaunator-cpp signed v1.0.0 release.
DISTNAME=	delaunator-1.0.0
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=abellgithub/}
GITHUB_PROJECT=	delaunator-cpp
GITHUB_TAG=	38474eec49d66cd35df597c955c2f3fc32928486
WRKSRC=		${WRKDIR}/delaunator-cpp-${GITHUB_TAG}
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/abellgithub/delaunator-cpp/
COMMENT=	C++ library for Delaunay triangulation of 2D points
LICENSE=	mit
USE_LANGUAGES=	c++
USE_CXX_FEATURES=	c++11
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
INSTALLATION_DIRS+=	share/licenses/delaunator
post-extract:
	${CP} ${FILESDIR}/delaunatorConfig.cmake.in ${WRKSRC}/cmake/delaunatorConfig.cmake.in
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/delaunator/LICENSE
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
