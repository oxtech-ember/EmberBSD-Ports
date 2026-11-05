# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME=	kicad-10.0.8
PKGNAME=	nanosvg-20261029
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_GITLAB:=kicad/code/}
GITLAB_PROJECT=	kicad
GITLAB_RELEASE=	10.0.8
EXTRACT_SUFX=	.tar.bz2
EXTRACT_ELEMENTS=	${DISTNAME}/thirdparty/nanosvg
WRKSRC=		${WRKDIR}/${DISTNAME}/thirdparty/nanosvg

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.com/kicad/code/kicad/-/tree/10.0.8/thirdparty/nanosvg
COMMENT=	KiCad-maintained NanoSVG parser library
LICENSE=	zlib

USE_LANGUAGES=	c++
USE_CXX_FEATURES=	c++11
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING:BOOL=ON
TEST_TARGET=	check

post-extract:
	${CP} ${FILESDIR}/nanosvg-file-api-consumer.cpp \
		${WRKSRC}/nanosvg-file-api-consumer.cpp

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/nanosvg
	${INSTALL_DATA} ${WRKSRC}/LICENSE.zlib \
		${DESTDIR}${PREFIX}/share/licenses/nanosvg/LICENSE.zlib

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
