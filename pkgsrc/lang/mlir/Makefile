# $NetBSD: Makefile,v 1.9 2026/03/25 22:56:27 wiz Exp $

.include "../../lang/llvm/version.mk"

PKGNAME=	mlir-${LLVM_VERSION}
CATEGORIES=	lang devel

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://mlir.llvm.org/
COMMENT=	Multi-Level Intermediate Representation
LICENSE=	apache-2.0

USE_CXX_FEATURES=	c++17
USE_LANGUAGES=		c c++
USE_TOOLS+=		gmake

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DMLIR_INCLUDE_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DMLIR_INCLUDE_INTEGRATION_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DMLIR_INSTALL_AGGREGATE_OBJECTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DMLIR_BUILD_MLIR_C_DYLIB=ON
# Fix for: lib 'MLIR' not found.
# MLIR_LINK_MLIR_DYLIB defaults to LLVM_LINK_LLVM_DYLIB, but libMLIR.so is not built.
# https://github.com/llvm/llvm-project/issues/181584
CMAKE_CONFIGURE_ARGS+=	-DMLIR_LINK_MLIR_DYLIB=OFF
# A standalone build only installs mlir-tblgen, mlir-pdll, mlir-src-sharder
# and tblgen-to-irdl, and exports them as imported targets for flang, when
# LLVM_BUILD_UTILS is on; the installed LLVMConfig.cmake does not set it.
CMAKE_CONFIGURE_ARGS+=	-DLLVM_BUILD_UTILS=ON

# Linalg's generator is built for the dialect but has no install rule.
# Cross mlir builds run it from the native package with the TableGen tools.
post-install:
	${INSTALL_PROGRAM} ${WRKSRC}/${CMAKE_BUILD_DIR}/bin/mlir-linalg-ods-yaml-gen \
	    ${DESTDIR}${PREFIX}/bin

.include "../../devel/cmake/build.mk"
.include "../../lang/llvm/buildlink3.mk"
CMAKE_CONFIGURE_ARGS+=	-DLLVM_DIR=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.llvm}/lib/cmake/llvm
CMAKE_CONFIGURE_ARGS+=	-DLLVM_CMAKE_DIR=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.llvm}/lib/cmake/llvm
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Generators run on the build host: take them from native LLVM and mlir.
.for _mlir_host_input in EMBERBSD_CROSS_BUILD_PYTHON EMBERBSD_LLVM_NATIVE_TOOLS EMBERBSD_MLIR_NATIVE_TOOLS
.if empty(${_mlir_host_input}:M/*) || !exists(${${_mlir_host_input}})
PKG_FAIL_REASON+= "${_mlir_host_input} must select the matching build-host tool"
.endif
.endfor
.include "../../lang/llvm/cross.mk"
.if !empty(EMBERBSD_MLIR_NATIVE_TOOLS:M/*)
_EMBERBSD_MLIR_TABLEGEN_VERSION!= if test -x ${EMBERBSD_MLIR_NATIVE_TOOLS:Q}/mlir-tblgen && \
    ember_mlir_banner=$$(${EMBERBSD_MLIR_NATIVE_TOOLS:Q}/mlir-tblgen --version); then \
    printf '%s\n' "$$ember_mlir_banner" | ${AWK} '/LLVM version/ { print $$NF; exit }'; fi
.endif
.if ${_EMBERBSD_MLIR_TABLEGEN_VERSION:U} != ${LLVM_VERSION}
PKG_FAIL_REASON+= "mlir-tblgen must execute on the build host and report LLVM ${LLVM_VERSION}"
.endif
.include "../../lang/llvm/cross-llvm-config.mk"
CMAKE_CONFIGURE_ARGS+=	-DPython3_EXECUTABLE=${EMBERBSD_CROSS_BUILD_PYTHON:Q}
CMAKE_CONFIGURE_ARGS+=	-DLLVM_TABLEGEN_EXE=${EMBERBSD_LLVM_NATIVE_TOOLS:Q}/llvm-tblgen
# add_tablegen and setup_host_tool read these settings; they derive the
# MLIR_*_EXE variables from them and would otherwise run target programs.
.for _mlir_tool _mlir_setting in mlir-tblgen MLIR_TABLEGEN mlir-pdll MLIR_PDLL_TABLEGEN \
    mlir-src-sharder MLIR_SRC_SHARDER_TABLEGEN \
    mlir-linalg-ods-yaml-gen MLIR_LINALG_ODS_YAML_GEN mlir-irdl-to-cpp MLIR_IRDL_TO_CPP
.if !empty(EMBERBSD_MLIR_NATIVE_TOOLS:M/*) && !exists(${EMBERBSD_MLIR_NATIVE_TOOLS}/${_mlir_tool})
PKG_FAIL_REASON+= "EMBERBSD_MLIR_NATIVE_TOOLS lacks the native ${_mlir_tool}"
.endif
CMAKE_CONFIGURE_ARGS+=	-D${_mlir_setting}=${EMBERBSD_MLIR_NATIVE_TOOLS:Q}/${_mlir_tool}
.endfor
.else
CMAKE_CONFIGURE_ARGS+=	-DPython3_EXECUTABLE=${TOOL_PYTHONBIN:Q}
.endif
.include "../../lang/python/tool.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
