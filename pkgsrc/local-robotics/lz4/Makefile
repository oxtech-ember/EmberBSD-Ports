# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), current common LZ4 package.
DISTNAME=	lz4-1.10.0
CATEGORIES=	archivers
MASTER_SITES=	https://codeload.github.com/lz4/lz4/tar.gz/
DISTFILES=	${DISTNAME}${EXTRACT_SUFX}
SITES.${DISTNAME}${EXTRACT_SUFX}= -https://codeload.github.com/lz4/lz4/tar.gz/ebb370ca83af193212df4dcbadcc5d87bc0de2f0
WRKSRC=	${WRKDIR}/lz4-ebb370ca83af193212df4dcbadcc5d87bc0de2f0

HOMEPAGE=	https://lz4.org/
COMMENT=	Fast lossless compression library and command line tools
LICENSE=	2-clause-bsd AND gnu-gpl-v2

USE_LANGUAGES=	c
GCC_REQD+=	16.2
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_MANDIR=man
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib\;${PREFIX}/gcc16/lib
CONFIGURE_DIRS=	build/cmake

post-install:
	${SH} ${FILESDIR}/install-stage.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
