# SPDX-License-Identifier: MIT
# Origin: EmberBSD, AI-assisted native Ruckig library package.
DISTNAME=	ruckig-0.19.4
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=pantor/}
GITHUB_PROJECT=	ruckig
GITHUB_TAG=	v${PKGVERSION_NOREV}

HOMEPAGE=	https://github.com/pantor/ruckig
COMMENT=	Jerk-limited trajectory generation for robots and machines
LICENSE=	mit

USE_LANGUAGES=		c++
USE_CXX_FEATURES=	c++20
CMAKE_REQD+=		3.15
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake

TEST_ENV+=	LD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}
TEST_ENV+=	DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}

do-test:
	# Use the upstream trajectory-count and seed arguments. Run every test group.
	${RUN} cd ${WRKSRC}/${CMAKE_BUILD_DIR} && \
	    ${SETENV} ${TEST_ENV} ./test-target 1000 42

INSTALLATION_DIRS+=	share/licenses/ruckig

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/ruckig/LICENSE
	${INSTALL_DATA} ${FILESDIR}/SOURCE ${DESTDIR}${PREFIX}/share/licenses/ruckig/SOURCE

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
