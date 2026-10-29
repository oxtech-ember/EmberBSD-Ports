# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), based on the official RTAB-Map release.
PKGREVISION=	2

.include "Makefile.common"

COMMENT=	Shared headless recorded-data mapping and localization core

CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_PREFIX=${PREFIX}
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The build runs rtabmap-res_tool on the build host to generate resources.
# A native Ports package of the same release provides it in TOOLBASE.
TOOL_DEPENDS+=	rtabmap-res-tool-0.23.8{,nb[0-9]*}:../../local-robotics/rtabmap-res-tool
CMAKE_CONFIGURE_ARGS+=	-DRTABMAP_RES_TOOL=${TOOLBASE:Q}/bin/rtabmap-res_tool
pre-configure: emberbsd-native-rtabmap-res-tool-check
.PHONY: emberbsd-native-rtabmap-res-tool-check
emberbsd-native-rtabmap-res-tool-check:
	${RUN}${TEST} -x ${TOOLBASE:Q}/bin/rtabmap-res_tool || { \
	    echo 'The native rtabmap-res_tool 0.23.8 is required' >&2; exit 1; \
	}
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
