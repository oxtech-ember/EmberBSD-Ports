# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= glslang-16.6.0
CATEGORIES= graphics
MASTER_SITES= ${MASTER_SITE_GITHUB:=KhronosGroup/}
GITHUB_TAG= ${PKGVERSION_NOREV}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/KhronosGroup/glslang/
COMMENT= Front end for GLSL/ESSL, HLSL and SPIR-V generator
LICENSE= modified-bsd AND 2-clause-bsd AND mit AND apache-2.0 AND gnu-gpl-v3

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 1
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
CMAKE_CONFIGURE_ARGS+= -DALLOW_EXTERNAL_SPIRV_TOOLS=ON
CMAKE_CONFIGURE_ARGS+= -DENABLE_OPT=ON
.include "../../devel/cmake/build.mk"
.include "../../lang/python/tool.mk"
BUILDLINK_API_DEPENDS.spirv-tools+= spirv-tools>=2026.4nb1
.include "../../parallel/spirv-tools/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
