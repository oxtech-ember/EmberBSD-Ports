# $NetBSD: Makefile,v 1.7 2026/08/07 10:42:20 kikadf Exp $

# Origin: EmberBSD contributors (AI-assisted); current component release.
DISTNAME=	SPIRV-Tools-2026.4
PKGNAME=	${DISTNAME:tl}
# nb2 rebuilds the native Darwin C++ ABI closure.
PKGREVISION=	2
CATEGORIES=	parallel
MASTER_SITES=	${MASTER_SITE_GITHUB:=KhronosGroup/}
GITHUB_PROJECT=	SPIRV-Tools
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/KhronosGroup/SPIRV-Tools/
COMMENT=	API and commands for processing SPIR-V modules
LICENSE=	apache-2.0

USE_TOOLS+=	pkg-config
USE_LANGUAGES=	c c++

PKGCONFIG_OVERRIDE+=	cmake/SPIRV-Tools-shared.pc.in
PKGCONFIG_OVERRIDE+=	cmake/SPIRV-Tools.pc.in

REPLACE_SH+=	tools/lesspipe/spirv-lesspipe.sh

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DSPIRV-Headers_SOURCE_DIR=${BUILDLINK_PREFIX.spirv-headers}
CMAKE_CONFIGURE_ARGS+=	-DSPIRV_USE_INSTALLED_GTEST=ON
CMAKE_CONFIGURE_ARGS+=	-DSPIRV_USE_INSTALLED_EFFCEE=ON
CMAKE_CONFIGURE_ARGS+=	-DSPIRV_SKIP_TESTS=OFF
TEST_TARGET=		test

.include "../../devel/cmake/build.mk"

# The shared C-interface test loads the uninstalled library from source/.
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
TEST_ENV+= LD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/source
TEST_ENV+= DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/source
.endif

.include "../../lang/python/tool.mk"
BUILDLINK_API_DEPENDS.googletest+=	googletest>=1.18.0
BUILDLINK_DEPMETHOD.googletest=	build
.include "../../devel/googletest/buildlink3.mk"
BUILDLINK_API_DEPENDS.effcee+=	effcee>=1.2026.0nb1
BUILDLINK_DEPMETHOD.effcee=	build
.include "../../devel/effcee/buildlink3.mk"
BUILDLINK_API_DEPENDS.re2+=	re2>=20251105nb3
BUILDLINK_DEPMETHOD.re2=		build
.include "../../devel/re2/buildlink3.mk"
BUILDLINK_API_DEPENDS.spirv-headers+=	spirv-headers>=1.4.363.0
.include "../../parallel/spirv-headers/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
