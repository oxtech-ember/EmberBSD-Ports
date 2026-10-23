# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), based on the official OpenCV release.
DISTNAME=	opencv-5.0.0
PKGNAME=	opencv5-5.0.0
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_GITHUB:=opencv/}
GITHUB_PROJECT=	opencv
GITHUB_TAG=	5.0.0

HOMEPAGE=	https://opencv.org/
COMMENT=	Shared headless image processing for recorded RGB-D mapping
LICENSE=	apache-2.0 AND modified-bsd AND mit AND ofl-v1.1
PATCH_STRIP=	-p1
CONFLICTS=	opencv-[0-9]*

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++17
GCC_REQD+=		16.2
CMAKE_REQD+=		3.22
PYTHON_FOR_BUILD_ONLY=	tool
PYTHON_VERSIONS_INCOMPATIBLE=	27
CMAKE_CONFIGURE_ARGS+=	-DPYTHON3_EXECUTABLE=${TOOL_PYTHONBIN}
CMAKE_CONFIGURE_ARGS+=	-DPYTHON_DEFAULT_EXECUTABLE=${TOOL_PYTHONBIN}
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_PREFIX=${PREFIX}
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib\;${PREFIX}/gcc16/lib
CMAKE_CONFIGURE_ARGS+=	-DJPEG_INCLUDE_DIR=${BUILDLINK_PREFIX.libjpeg-turbo}/include
CMAKE_CONFIGURE_ARGS+=	-DJPEG_LIBRARY_RELEASE=${BUILDLINK_PREFIX.libjpeg-turbo}/lib/libjpeg.so
CMAKE_CONFIGURE_ARGS+=	-DPNG_PNG_INCLUDE_DIR=${BUILDLINK_PREFIX.png}/include
CMAKE_CONFIGURE_ARGS+=	-DPNG_LIBRARY_RELEASE=${BUILDLINK_PREFIX.png}/lib/libpng16.so

post-install:
	${SH} ${FILESDIR}/install-licenses.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../devel/cmake/build.mk"
.include "../../lang/python/tool.mk"
# Installed CMake and pkg-config files require the Eigen headers.
BUILDLINK_DEPMETHOD.eigen3=	full
.include "../../math/eigen3/buildlink3.mk"
.include "../../graphics/libjpeg-turbo/buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
