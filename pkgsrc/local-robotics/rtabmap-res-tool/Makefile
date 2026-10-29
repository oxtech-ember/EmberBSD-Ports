# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), based on the official RTAB-Map release.
.include "../../local-robotics/rtabmap/Makefile.common"

PKGNAME=	${DISTNAME:S/^rtabmap-/rtabmap-res-tool-/}
COMMENT=	RTAB-Map resource generator for cross builds

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# Upstream's resource-only branch builds the static utilite and the tool.
# ANDROID_PREBUILD names that branch; it does not select an Android target.
CMAKE_CONFIGURE_ARGS+=	-DANDROID_PREBUILD=ON
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_CXX_STANDARD=17
BUILD_TARGET=		res_tool

INSTALLATION_DIRS=	bin

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/${CMAKE_BUILD_DIR}/bin/rtabmap-res_tool \
	    ${DESTDIR}${PREFIX}/bin/rtabmap-res_tool

.include "../../devel/cmake/build.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
