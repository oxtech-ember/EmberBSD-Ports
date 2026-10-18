# $NetBSD: Makefile,v 1.89 2026/08/23 07:48:26 wiz Exp $

# Origin: pkgsrc; EmberBSD common-provider update (AI-assisted).
DISTNAME=	openexr-3.5.2
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_GITHUB:=AcademySoftwareFoundation/}
GITHUB_PROJECT=	openexr
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	adam@NetBSD.org
HOMEPAGE=	https://www.openexr.com/
COMMENT=	High dynamic-range (HDR) image file format library and tools
LICENSE=	modified-bsd

USE_LANGUAGES=	c c++
GCC_REQD+=	16.2
CMAKE_REQD+=	4.4.4

USE_CXX_FEATURES+=	c++17 filesystem

USE_TOOLS+=	pkg-config

PKGCONFIG_OVERRIDE=	cmake/OpenEXR.pc.in

PTHREAD_OPTS=	require

# Issue 1594 is fixed upstream. Retain library and command-line tests.
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=ON -DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
CMAKE_CONFIGURE_ARGS+= -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DOPENEXR_REQUIRE_SYSTEM_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DPython3_EXECUTABLE:FILEPATH=${TOOL_PYTHONBIN}
PYTHON_FOR_BUILD_ONLY= tool
PYTHON_VERSION_REQD= 315
TEST_TARGET= test

CHECK_PORTABILITY_SKIP+=	Contrib/DtexToExr/bootstrap
CHECK_PORTABILITY_SKIP+=	share/util/reformat.sh

.include "../../lang/python/tool.mk"
.include "../../devel/cmake/build.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
BUILDLINK_API_DEPENDS.libdeflate+= libdeflate>=1.26
.include "../../devel/libdeflate/buildlink3.mk"
BUILDLINK_API_DEPENDS.OpenJPH+= OpenJPH>=0.32.0
.include "../../graphics/OpenJPH/buildlink3.mk"
BUILDLINK_API_DEPENDS.imath+= imath>=3.2.3
.include "../../math/imath/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
