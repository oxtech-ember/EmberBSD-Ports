# $NetBSD: Makefile,v 1.18 2026/03/25 22:56:26 wiz Exp $

.include "../../lang/llvm/version.mk"

PKGNAME=	flang-${LLVM_VERSION}
PKGREVISION=	2
CATEGORIES=	lang devel

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://flang.llvm.org/docs/
COMMENT=	Fortran compiler targeting LLVM
LICENSE=	apache-2.0

USE_CXX_FEATURES+=	c++17
USE_LANGUAGES=		c c++
USE_TOOLS+=		gmake

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DFLANG_INCLUDE_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DLLVM_ENABLE_PEDANTIC=OFF
CMAKE_CONFIGURE_ARGS+=	-DCLANG_DIR=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.clang}/lib/cmake/clang
CMAKE_CONFIGURE_ARGS+=	-DLLVM_DIR=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.llvm}/lib/cmake/llvm
CMAKE_CONFIGURE_ARGS+=	-DMLIR_DIR=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.mlir}/lib/cmake/mlir
# MLIR is installed as static libraries only.  Shared flang libraries would
# each carry their own copy of MLIR and its registries, and flang crashes
# while it registers the MLIR dialects, so link MLIR once into each program.
# LLVM itself is still linked through libLLVM.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=OFF

.include "../../devel/cmake/build.mk"
.include "../../lang/clang/buildlink3.mk"
.include "../../lang/llvm/buildlink3.mk"
.include "../../lang/mlir/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The MLIR TableGen generator runs on the build host. MLIRConfig.cmake names
# the installed target mlir-tblgen; take it from the native mlir instead.
.if empty(EMBERBSD_MLIR_NATIVE_TOOLS:M/*) || !exists(${EMBERBSD_MLIR_NATIVE_TOOLS}/mlir-tblgen)
PKG_FAIL_REASON+= "EMBERBSD_MLIR_NATIVE_TOOLS must name a directory with the build-host mlir-tblgen"
.else
_EMBERBSD_MLIR_TABLEGEN_VERSION!= if ember_mlir_banner=$$(${EMBERBSD_MLIR_NATIVE_TOOLS:Q}/mlir-tblgen --version); then \
    printf '%s\n' "$$ember_mlir_banner" | ${AWK} '/LLVM version/ { print $$NF; exit }'; fi
.if ${_EMBERBSD_MLIR_TABLEGEN_VERSION:U} != ${LLVM_VERSION}
PKG_FAIL_REASON+= "mlir-tblgen must execute on the build host and report LLVM ${LLVM_VERSION}"
.endif
.endif
CMAKE_CONFIGURE_ARGS+=	-DMLIR_TABLEGEN=${EMBERBSD_MLIR_NATIVE_TOOLS:Q}/mlir-tblgen
.endif
.include "../../mk/bsd.pkg.mk"
