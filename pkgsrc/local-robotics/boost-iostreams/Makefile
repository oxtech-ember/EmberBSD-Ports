# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), non-overlapping common Boost component.
DISTNAME=	boost-1.92.0-cmake
PKGNAME=	boost-iostreams-1.92.0
WRKSRC=	${WRKDIR}/boost-1.92.0
CATEGORIES=	devel
MASTER_SITES=	https://github.com/boostorg/boost/releases/download/boost-1.92.0/
EXTRACT_SUFX=	.tar.xz
DISTINFO_FILE=	${.CURDIR}/../boost-libs/distinfo

HOMEPAGE=	https://www.boost.org/
COMMENT=	Boost Iostreams and Random with base compression libraries
LICENSE=	boost-license
DEPENDS+=	boost-headers-1.92.0{,nb*}:../../local-robotics/boost-headers

USE_LANGUAGES=	c c++
USE_CXX_FEATURES=	c++17
GCC_REQD+=	16.2
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib\;${PREFIX}/gcc16/lib

post-install:
	${SH} ${FILESDIR}/install-stage.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../devel/cmake/build.mk"
.include "../../local-robotics/boost-headers/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../archivers/bzip2/buildlink3.mk"
.include "../../archivers/xz/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
