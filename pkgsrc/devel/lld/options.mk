# $NetBSD: options.mk,v 1.2 2024/08/25 06:18:36 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.lld
PKG_SUPPORTED_OPTIONS=	tests
PKG_SUGGESTED_OPTIONS+=	tests

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mtests)
EXTRACT_ELEMENTS+=	${DISTNAME}/llvm
BUILDLINK_DEPMETHOD.googletest= build
.include "../../devel/googletest/buildlink3.mk"
CMAKE_CONFIGURE_ARGS+=		-DLLVM_INCLUDE_TESTS=ON
CMAKE_CONFIGURE_ARGS+=		-DLLVM_BUILD_TESTS=ON
CMAKE_CONFIGURE_ARGS+=		-DLLVM_MAIN_SRC_DIR=${WRKDIR}/${DISTNAME}/llvm
USE_TOOLS+=		od:test
TEST_DEPENDS+=		coreutils-[0-9]*:../../sysutils/coreutils
TOOLS_PLATFORM.od:=	${TOOLBASE}/${PKGGNUDIR}bin/od
TOOLS_PATH.od:=		${TOOLBASE}/${PKGGNUDIR}bin/od
TEST_TARGET=		check-lld  # failing tests fixed in 8.0
TEST_ENV+=		LD_LIBRARY_PATH=${WRKDIR}/build/lib
TEST_ENV+=		LC_ALL=C
.else
CMAKE_CONFIGURE_ARGS+=		-DLLVM_INCLUDE_TESTS=OFF
.endif
