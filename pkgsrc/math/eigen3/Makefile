# $NetBSD: Makefile,v 1.21 2025/08/20 11:35:05 wiz Exp $
# Origin: pkgsrc math/eigen3; EmberBSD (AI-assisted) current Eigen release.

DISTNAME=	eigen-5.0.1
PKGNAME=	${DISTNAME:S/eigen/eigen3/}
PKGREVISION=	1
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITLAB:=libeigen/eigen/-/archive/${PKGVERSION_NOREV}/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://libeigen.gitlab.io/
COMMENT=	C++ template library for linear algebra
LICENSE=	mpl-2.0

USE_LANGUAGES=	c c++
USE_CXX_FEATURES=	c++14

# Use the upstream CMake and pkg-config locations: share/eigen3/cmake and
# share/pkgconfig. Whether the package keeps the BLAS and LAPACK libraries
# is an open decision; this recipe keeps the upstream default.

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_EXPORT_PACKAGE_REGISTRY=OFF
CMAKE_CONFIGURE_ARGS+=	-DEIGEN_BUILD_PKGCONFIG=ON
# The release archive's Eigen/Version has an empty prerelease identifier.
# Upstream CMake otherwise supplies "dev" instead of reading that identifier.
CMAKE_CONFIGURE_ARGS+=	-DEIGEN_PRERELEASE_VERSION=

INSTALLATION_DIRS+=	share/licenses/eigen3

post-install:
.for name in APACHE BSD MINPACK MPL2 README
	${INSTALL_DATA} ${WRKSRC}/COPYING.${name} \
	    ${DESTDIR}${PREFIX}/share/licenses/eigen3/COPYING.${name}
.endfor

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
