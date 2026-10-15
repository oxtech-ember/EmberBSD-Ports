# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), current common Eigen source package.
DISTNAME=	eigen-5.0.1
PKGNAME=	eigen3-5.0.1
CATEGORIES=	math
MASTER_SITES=	https://gitlab.com/libeigen/eigen/-/archive/5.0.1/

HOMEPAGE=	https://libeigen.gitlab.io/
COMMENT=	C++ template library for linear algebra
LICENSE=	mpl-2.0

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++17
GCC_REQD+=		16.2
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DEIGEN_BUILD_TESTING=OFF -DEIGEN_BUILD_DOC=OFF
CMAKE_CONFIGURE_ARGS+=	-DEIGEN_BUILD_BLAS=OFF -DEIGEN_BUILD_LAPACK=OFF
CMAKE_CONFIGURE_ARGS+=	-DEIGEN_BUILD_DEMOS=OFF

INSTALLATION_DIRS+=	share/licenses/eigen3

post-install:
	${INSTALL_DATA} ${WRKSRC}/COPYING.MPL2 ${DESTDIR}${PREFIX}/share/licenses/eigen3/LICENSE
	${INSTALL_DATA} ${WRKSRC}/COPYING* ${DESTDIR}${PREFIX}/share/licenses/eigen3/
	${INSTALL_DATA} ${FILESDIR}/SOURCE ${DESTDIR}${PREFIX}/share/licenses/eigen3/SOURCE

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
