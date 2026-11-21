# Native Zenoh-Pico library and development interfaces.
DISTNAME=	zenoh-pico-1.10.2
CATEGORIES=	net
MASTER_SITES=	${MASTER_SITE_GITHUB:=eclipse-zenoh/}
GITHUB_PROJECT=	zenoh-pico
GITHUB_TAG=	6a881c21dad1f778d0529eb9f297bea339016526
WRKSRC=		${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}

HOMEPAGE=	https://github.com/eclipse-zenoh/zenoh-pico
COMMENT=	Native C Zenoh publish/subscribe library for embedded devices
LICENSE=	apache-2.0

USE_LANGUAGES=		c
USE_CC_FEATURES=		c11
TOOL_DEPENDS+=		cmake>=3.14:../../devel/cmake
TEST_DEPENDS+=		bash-[0-9]*:../../shells/bash
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+=	-DBUILD_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=ON
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TOOLS=OFF
CMAKE_CONFIGURE_ARGS+=	-DZ_FEATURE_AUTO_RECONNECT=1

do-test:
	# Timing-sensitive upstream tests also run on single-CPU guests.
	cd ${WRKSRC}/${CMAKE_BUILD_DIR} && ${SETENV} LD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/lib ctest --output-on-failure --timeout 180 -j1

INSTALLATION_DIRS+=	share/licenses/zenoh-pico
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${WRKSRC}/NOTICE.md \
	    ${FILESDIR}/SOURCE ${DESTDIR}${PREFIX}/share/licenses/zenoh-pico/

.include "../../devel/cmake/build.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
