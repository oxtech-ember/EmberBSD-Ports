# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).

DISTNAME= spirv-cross-1.4.363.0
CATEGORIES= graphics
MASTER_SITES= ${MASTER_SITE_GITHUB:=KhronosGroup/}
GITHUB_PROJECT= SPIRV-Cross
GITHUB_TAG= vulkan-sdk-${PKGVERSION_NOREV}
WRKSRC= ${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/KhronosGroup/SPIRV-Cross/
COMMENT= SPIR-V reflection and translation library and tools
LICENSE= apache-2.0 AND mit

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 2
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
PLIST_VARS+= darwin unix
.if ${OPSYS} == "Darwin"
PLIST.darwin= yes
.else
PLIST.unix= yes
.endif
CMAKE_CONFIGURE_ARGS+= -DSPIRV_CROSS_SHARED=ON
CMAKE_CONFIGURE_ARGS+= -DSPIRV_CROSS_STATIC=ON
CMAKE_CONFIGURE_ARGS+= -DSPIRV_CROSS_CLI=ON
CMAKE_CONFIGURE_ARGS+= -DSPIRV_CROSS_ENABLE_TESTS=ON
CMAKE_CONFIGURE_ARGS+= -DPython3_EXECUTABLE=${TOOL_PYTHONBIN}
TEST_TARGET= test

.include "../../devel/cmake/build.mk"
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
