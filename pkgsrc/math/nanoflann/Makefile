# $NetBSD$

DISTNAME=	nanoflann-2.0.1
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=jlblancoc/}
GITHUB_TAG=	${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/jlblancoc/nanoflann
COMMENT=	Header-only nearest-neighbor search library
LICENSE=	2-clause-bsd

USE_LANGUAGES=	c c++
CMAKE_CONFIGURE_ARGS+=	-DNANOFLANN_BUILD_EXAMPLES:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DNANOFLANN_BUILD_TESTS:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING:BOOL=OFF

INSTALLATION_DIRS+=	share/licenses/nanoflann
post-install:
	${INSTALL_DATA} ${WRKSRC}/COPYING \
		${DESTDIR}${PREFIX}/share/licenses/nanoflann/COPYING

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
