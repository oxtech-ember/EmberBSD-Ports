# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), shared current FLANN C++ package.
DISTNAME=	flann-1.9.2
PKGNAME=	${DISTNAME:S/-/-lib-/}
PKGREVISION=	1
CATEGORIES=	math
MASTER_SITES=	https://codeload.github.com/flann-lib/flann/tar.gz/
DISTFILES=	${DISTNAME}${EXTRACT_SUFX}
SITES.${DISTNAME}${EXTRACT_SUFX}= -https://codeload.github.com/flann-lib/flann/tar.gz/c50f296b0b27e14667d272b37acc63f949b305c4
WRKSRC=	${WRKDIR}/flann-c50f296b0b27e14667d272b37acc63f949b305c4

HOMEPAGE=	https://github.com/flann-lib/flann
COMMENT=	Fast library for approximate nearest-neighbor search
LICENSE=	modified-bsd

USE_LANGUAGES=	c c++
USE_CXX_FEATURES=	c++17
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_CXX_EXTENSIONS=OFF -DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_POLICY_VERSION_MINIMUM=3.5
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib

post-install:
	${SH} ${FILESDIR}/install-stage.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../devel/cmake/build.mk"
.include "../../archivers/lz4/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
