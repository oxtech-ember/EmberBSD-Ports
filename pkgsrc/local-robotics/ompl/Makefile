# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), based on the upstream OMPL release.
DISTNAME=	ompl-2.0.2
PKGREVISION=	1
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=ompl/}
GITHUB_PROJECT=	ompl
GITHUB_RELEASE=	${PKGVERSION_NOREV}

HOMEPAGE=	https://ompl.kavrakilab.org/
COMMENT=	Sampling-based motion planning library
LICENSE=	modified-bsd

USE_LANGUAGES=		c++
USE_CXX_FEATURES=	c++17
GCC_REQD+=		16.2
CMAKE_REQD+=		3.22
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib

INSTALLATION_DIRS+=	share/licenses/ompl

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/ompl/LICENSE
	${INSTALL_DATA} ${FILESDIR}/SOURCE ${DESTDIR}${PREFIX}/share/licenses/ompl/SOURCE

.include "../../devel/cmake/build.mk"
# Installed CMake and pkg-config files require the Eigen headers.
BUILDLINK_DEPMETHOD.eigen3=	full
.include "../../math/eigen3/buildlink3.mk"
.include "../../devel/boost-libs/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
