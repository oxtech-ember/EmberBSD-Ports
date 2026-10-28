# $NetBSD: Makefile,v 1.28 2026/03/25 22:56:24 wiz Exp $

.include "../../lang/llvm/version.mk"

# Mach-O consumes the matching source header; no libunwind runtime is installed.
EXTRACT_ELEMENTS+= ${DISTNAME}/libunwind/include

PKGNAME=	lld-${LLVM_VERSION}
PKGREVISION=	5
CATEGORIES=	devel

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://lld.llvm.org/
COMMENT=	The LLVM Linker
LICENSE=	apache-2.0

USE_CXX_FEATURES=	c++17
USE_LANGUAGES=		c c++
GCC_REQD+=		16.2

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release

PYTHON_VERSIONS_ACCEPTED= 315
PYTHON_FOR_BUILD_ONLY=	tool

INSTALLATION_DIRS+=	libexec/lld

post-install:
	${LN} -sf ../../bin/lld ${DESTDIR}${PREFIX}/libexec/lld/ld

.include "options.mk"
.include "../../devel/cmake/build.mk"
BUILDLINK_API_DEPENDS.llvm+=	llvm-${LLVM_VERSION}{,nb*}
.include "../../lang/llvm/buildlink3.mk"
.include "../../devel/py-llvm-lit/buildlink3.mk"
CMAKE_CONFIGURE_ARGS+=	-DLLVM_DIR=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.llvm}/lib/cmake/llvm
CMAKE_CONFIGURE_ARGS+=	-DLLVM_CMAKE_DIR=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.llvm}/lib/cmake/llvm
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.for _lld_host_input in EMBERBSD_CROSS_BUILD_PYTHON EMBERBSD_CROSS_LLVM_CONFIG EMBERBSD_LLVM_NATIVE_TOOLS
.if empty(${_lld_host_input}:M/*) || !exists(${${_lld_host_input}})
PKG_FAIL_REASON+= "${_lld_host_input} must select the matching build-host tool"
.endif
.endfor
# CMake resolves symlinked sysroots. Map that spelling into the declared
# buildlink headers, as for the shared graphics introspection consumers.
_EMBERBSD_LLD_REAL_SYSROOT!= cd ${CROSS_DESTDIR:Q} && pwd -P
BUILDLINK_TRANSFORM+= I:${_EMBERBSD_LLD_REAL_SYSROOT}${PREFIX}:${BUILDLINK_DIR}
LLVM_CONFIG_PATH= ${EMBERBSD_CROSS_LLVM_CONFIG}
CMAKE_CONFIGURE_ARGS+= -DLLVM_TABLEGEN_EXE=${EMBERBSD_LLVM_NATIVE_TOOLS:Q}/llvm-tblgen
TOOL_DEPENDS+= ${PYPKGPREFIX}-llvm-lit>=${LLVM_VERSION}:../../devel/py-llvm-lit
CMAKE_CONFIGURE_ARGS+= -DLLVM_EXTERNAL_LIT=${TOOLBASE:Q}/bin/llvm-lit
CMAKE_CONFIGURE_ARGS+= -DPython3_EXECUTABLE=${EMBERBSD_CROSS_BUILD_PYTHON:Q}
.else
CMAKE_CONFIGURE_ARGS+= -DPython3_EXECUTABLE=${TOOL_PYTHONBIN:Q}
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
CMAKE_CONFIGURE_ARGS+= -DLLVM_EXTERNAL_LIT=${BUILDLINK_PREFIX.py-llvm-lit:Q}/bin/llvm-lit
.endif
CMAKE_CONFIGURE_ARGS+=	-DLLVM_INSTALL_TOOLCHAIN_ONLY=OFF
.if !empty(PKG_OPTIONS:Mtests) && empty(PKG_BUILD_OPTIONS.llvm:Mtests)
PKG_FAIL_REASON+= "LLD tests require matching LLVM llvm_gtest exports (tests option)"
.endif
.include "../../lang/python/tool.mk"
.include "../../mk/atomic64.mk"

pre-configure:
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${TEST} "$$(${EMBERBSD_LLVM_NATIVE_TOOLS}/llvm-tblgen --version | ${AWK} '/LLVM version/ {print $$3; exit}')" = "${LLVM_VERSION}"
	${TEST} "$$(${TOOLBASE}/bin/llvm-lit --version | ${AWK} '{sub(/dev$$/, "", $$2); print $$2}')" = "${LLVM_VERSION}"
.endif
	${TEST} "`${LLVM_CONFIG_PATH} --version`" = "${LLVM_VERSION}"

.include "../../mk/bsd.pkg.mk"
