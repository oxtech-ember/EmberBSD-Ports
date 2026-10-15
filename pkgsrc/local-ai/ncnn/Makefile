# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), based on the official ncnn release.
DISTNAME=	ncnn-20260526
CATEGORIES=	math
MASTER_SITES=	-https://codeload.github.com/Tencent/ncnn/tar.gz/refs/tags/20260526

HOMEPAGE=	https://github.com/Tencent/ncnn
COMMENT=	Shared ncnn CPU inference C and C++ API
LICENSE=	modified-bsd AND zlib
PATCH_STRIP=	-p1

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++11
GCC_REQD+=		16.2
CMAKE_REQD+=		3.10
USE_TOOLS+=		gmake
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib\;${PREFIX}/gcc16/lib

INSTALLATION_DIRS+=	share/licenses/ncnn share/doc/ncnn
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE.txt ${DESTDIR}${PREFIX}/share/licenses/ncnn/LICENSE.txt
	${INSTALL_DATA} ${FILESDIR}/SOURCE ${DESTDIR}${PREFIX}/share/doc/ncnn/SOURCE

.include "../../devel/cmake/build.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
