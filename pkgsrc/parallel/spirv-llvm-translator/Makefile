# $NetBSD: Makefile,v 1.18 2026/09/02 14:11:41 adam Exp $
# Origin: EmberBSD contributors (AI-assisted); LLVM 23.1 release family.

# Note that parallel/spirv-headers must be kept in sync with what this
# package expects.
DISTNAME=	SPIRV-LLVM-Translator-23.1.3
PKGNAME=	${DISTNAME:tl}

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 1
DEPENDS+= libcxx>=23.1.6:../../lang/libcxx
DEPENDS+= llvm>=23.1.6nb1:../../lang/llvm
BUILD_DEPENDS+= clang>=23.1.6nb1<23.2:../../lang/clang
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
CATEGORIES=	parallel
MASTER_SITES=	${MASTER_SITE_GITHUB:=KhronosGroup/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/KhronosGroup/SPIRV-LLVM-Translator
COMMENT=	Tool and library for translation between SPIR-V and LLVM IR
LICENSE=	modified-bsd

WRKSRC=		${WRKDIR}/${DISTNAME}

USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config

CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+=	-DCCACHE_ALLOWED=OFF
# The upstream path is a prefix that contains include/spirv. Use the same
# buildlink view for native and cross inputs. Do not fetch another header tree.
CMAKE_CONFIGURE_ARGS+=	-DLLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR=${BUILDLINK_DIR}

PKG_OPTIONS_VAR=	PKG_OPTIONS.spirv-llvm-translator
PKG_SUPPORTED_OPTIONS=	tests
.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mtests)
CMAKE_CONFIGURE_ARGS+=	-DLLVM_SPIRV_INCLUDE_TESTS=ON
CMAKE_CONFIGURE_ARGS+=	-DLLVM_EXTERNAL_LIT=${TOOLBASE}/bin/llvm-lit
CMAKE_CONFIGURE_ARGS+=	-DPython3_EXECUTABLE=${TOOL_PYTHONBIN}
TEST_TARGET=	check-llvm-spirv
# Clang translates shader test inputs; the selected compiler builds package objects.
TOOL_DEPENDS+=	clang>=23.1.4<23.2:../../lang/clang
TOOL_DEPENDS+=	${PYPKGPREFIX}-llvm-lit>=23.1.4<23.2:../../devel/py-llvm-lit
.include "../../lang/python/tool.mk"
.else
CMAKE_CONFIGURE_ARGS+=	-DLLVM_SPIRV_INCLUDE_TESTS=OFF
pre-test:
	@${ERROR_MSG} "The upstream suite requires PKG_OPTIONS.spirv-llvm-translator+=tests"
	${FALSE}
.endif

PKGCONFIG_OVERRIDE+=	LLVMSPIRVLib.pc.in

.include "../../devel/cmake/build.mk"
BUILDLINK_API_DEPENDS.llvm+= llvm>=23.1.4<23.2
.include "../../lang/llvm/buildlink3.mk"
BUILDLINK_API_DEPENDS.spirv-headers+= spirv-headers>=1.4.363.0nb2
.include "../../parallel/spirv-headers/buildlink3.mk"
BUILDLINK_API_DEPENDS.spirv-tools+= spirv-tools>=2026.4nb1
.include "../../parallel/spirv-tools/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
