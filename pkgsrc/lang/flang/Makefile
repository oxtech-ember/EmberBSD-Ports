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
CMAKE_CONFIGURE_ARGS+=	-DCLANG_DIR=${BUILDLINK_PREFIX.clang}/lib/cmake/clang
CMAKE_CONFIGURE_ARGS+=	-DLLVM_DIR=${BUILDLINK_PREFIX.llvm}/lib/cmake/llvm
CMAKE_CONFIGURE_ARGS+=	-DMLIR_DIR=${BUILDLINK_PREFIX.mlir}/lib/cmake/mlir
# MLIR is installed as static libraries only.  Shared flang libraries would
# each carry their own copy of MLIR and its registries, and flang crashes
# while it registers the MLIR dialects, so link MLIR once into each program.
# LLVM itself is still linked through libLLVM.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=OFF

.include "../../devel/cmake/build.mk"
.include "../../lang/clang/buildlink3.mk"
.include "../../lang/llvm/buildlink3.mk"
.include "../../lang/mlir/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
