# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), based on the official GTSAM release.
DISTNAME=	gtsam-4.3.0
PKGREVISION=	1
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=borglab/}
GITHUB_PROJECT=	gtsam
GITHUB_TAG=	71a25ca36c084cbad1f872e812d6d97fbadfdb05
WRKSRC=		${WRKDIR}/gtsam-${GITHUB_TAG}

HOMEPAGE=	https://gtsam.org/
COMMENT=	Factor-graph optimization for sensor fusion
LICENSE=	modified-bsd AND mpl-2.0 AND mit AND boost-license

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++17
CMAKE_REQD+=		3.22
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib
BUILD_TARGET=		gtsam CppUnitLite

post-install:
	${SH} ${FILESDIR}/install-licenses.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../devel/cmake/build.mk"
# Installed CMake and pkg-config files require the Eigen headers.
BUILDLINK_DEPMETHOD.eigen3=	full
.include "../../math/eigen3/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
