# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), based on the official PCL release.
DISTNAME=	pcl-1.15.1
PKGREVISION=	2
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_GITHUB:=PointCloudLibrary/}
GITHUB_PROJECT=	pcl
GITHUB_TAG=	3346843ea6b97697a1577293aa9cdf236b5c7ffb
WRKSRC=		${WRKDIR}/pcl-${GITHUB_TAG}

HOMEPAGE=	https://pointclouds.org/
COMMENT=	Shared point-cloud geometry for filtering, registration and mapping
LICENSE=	modified-bsd AND 2-clause-bsd
PATCH_STRIP=	-p1

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++17
CMAKE_REQD+=		3.22
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_PREFIX=${PREFIX}
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib
BUILD_TARGET=		pcl_common pcl_kdtree pcl_octree pcl_search
BUILD_TARGET+=		pcl_sample_consensus pcl_filters pcl_features
BUILD_TARGET+=		pcl_registration pcl_io pcl_io_ply
BUILD_TARGET+=		pcl_surface pcl_segmentation pcl_ml

post-install:
	${SH} ${FILESDIR}/install-licenses.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../devel/cmake/build.mk"
# Installed CMake and pkg-config files require the Eigen headers.
BUILDLINK_DEPMETHOD.eigen3=	full
.include "../../math/eigen3/buildlink3.mk"
.include "../../devel/boost-libs/buildlink3.mk"
.include "../../math/flann-lib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
