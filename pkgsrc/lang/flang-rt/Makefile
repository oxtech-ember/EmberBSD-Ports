# $NetBSD$

.include "../../lang/llvm/version.mk"

PKGNAME=	flang-rt-${LLVM_VERSION}
PKGREVISION=	1
CATEGORIES=	lang devel

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://flang.llvm.org/docs/
COMMENT=	Runtime library and intrinsic modules for LLVM Flang
LICENSE=	apache-2.0

# Flang-RT builds only through the LLVM runtimes build, which reads the LLVM
# CMake modules and the Flang headers.
WRKSRC=			${WRKDIR}/${DISTNAME}/runtimes
EXTRACT_ELEMENTS+=	${DISTNAME}/llvm
EXTRACT_ELEMENTS+=	${DISTNAME}/flang

USE_CXX_FEATURES+=	c++17
# Fortran is built by the Flang named below, not by the pkgsrc Fortran
# provider: the runtime and intrinsic modules must match that Flang.
USE_LANGUAGES=		c c++

TOOL_DEPENDS+=		flang>=${LLVM_VERSION}nb1:../../lang/flang

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DLLVM_ENABLE_RUNTIMES=flang-rt
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_Fortran_COMPILER=${TOOLBASE}/bin/flang
# CMake's Fortran compiler check links a program, which needs the runtime
# this package builds; check by compiling only.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
CMAKE_CONFIGURE_ARGS+=	-DLLVM_INCLUDE_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DFLANG_RT_INCLUDE_TESTS=OFF
# Fortran shared libraries link the static runtime into themselves.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_POSITION_INDEPENDENT_CODE=ON
# Install into the Flang resource directory, as compiler-rt does for Clang.
# The runtimes build always uses lib/<triple> outside Darwin, which the
# driver searches as well.  The path must be typed: an untyped relative
# value is made absolute against the configure directory.
CMAKE_CONFIGURE_ARGS+=	-DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=OFF
CMAKE_CONFIGURE_ARGS+=	-DRUNTIMES_INSTALL_RESOURCE_PATH:STRING=lib/clang/${LLVM_MAJOR_VERSION}
# Name the target explicitly so the library and module directories match
# the PLIST, and so a cross build compiles for the target.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_Fortran_COMPILER_TARGET=${MACHINE_GNU_PLATFORM}
CMAKE_CONFIGURE_ARGS+=	-DLLVM_DEFAULT_TARGET_TRIPLE=${MACHINE_GNU_PLATFORM}
PLIST_SUBST+=		FLANG_RT_TRIPLE=${MACHINE_GNU_PLATFORM}

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
