# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), based on the official RTAB-Map release.
DISTNAME=	rtabmap-0.23.8
CATEGORIES=	geography
MASTER_SITES=	${MASTER_SITE_GITHUB:=introlab/}
GITHUB_PROJECT=	rtabmap
GITHUB_TAG=	d069becc724905d6465a8758c40dae88e13bb9e8
WRKSRC=		${WRKDIR}/rtabmap-${GITHUB_TAG}

HOMEPAGE=	https://introlab.github.io/rtabmap/
COMMENT=	Shared headless recorded-data mapping and localization core
LICENSE=	modified-bsd AND 2-clause-bsd AND mit AND gnu-lgpl-v3
PATCH_STRIP=	-p1

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++17
GCC_REQD+=		16.2
CMAKE_REQD+=		3.22
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_PREFIX=${PREFIX}
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib\;${PREFIX}/gcc16/lib

# Build this host tool with probes/rtabmap/build-resource-tool.sh first.
.include "../../mk/bsd.prefs.mk"
.if !empty(USE_CROSS_COMPILE:M[yY][eE][sS])
.if !defined(RTABMAP_NATIVE_RES_TOOL)
PKG_FAIL_REASON+=	"Set RTABMAP_NATIVE_RES_TOOL to the genuine native rtabmap-res_tool"
.else
CMAKE_CONFIGURE_ARGS+=	-DRTABMAP_RES_TOOL=${RTABMAP_NATIVE_RES_TOOL}
.endif
.endif

post-install:
	${SH} ${FILESDIR}/install-licenses.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../devel/cmake/build.mk"
.include "../../graphics/opencv/buildlink3.mk"
.include "../../graphics/pcl/buildlink3.mk"
.include "../../local-robotics/gtsam/buildlink3.mk"
.include "../../databases/sqlite3/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
