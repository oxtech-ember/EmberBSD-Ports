# $NetBSD: Makefile,v 1.16 2026/08/03 18:09:30 wiz Exp $
#
# Note: every non-micro update currently incurs a recursive bump
# https://github.com/aous72/OpenJPH/issues/304

# Origin: pkgsrc; EmberBSD common-provider update (AI-assisted).
DISTNAME=	OpenJPH-0.32.0
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_GITHUB:=aous72/}
GITHUB_TAG=	${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/aous72/OpenJPH/
COMMENT=	Open-source implementation of JPEG2000 Part-15
LICENSE=	2-clause-bsd

CMAKE_REQD+=	4.4.4
USE_CC_FEATURES=	c11
USE_CXX_FEATURES=	c++14
USE_LANGUAGES=		c c++

PKGCONFIG_OVERRIDE+=		${CMAKE_BUILD_DIR}/openjph.pc
PKGCONFIG_OVERRIDE_STAGE=	post-build

# Upstream detects target SIMD. The retired INTEL_SIMD option disables all SIMD.
CMAKE_CONFIGURE_ARGS+= -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_REQUIRE_FIND_PACKAGE_TIFF=ON

.include "../../devel/cmake/build.mk"
.include "../../graphics/tiff/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
