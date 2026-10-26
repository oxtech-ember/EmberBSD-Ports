# $NetBSD: Makefile,v 1.29 2026/03/25 22:56:26 wiz Exp $

.include "../../lang/llvm/version.mk"

PKGNAME=	compiler-rt-${LLVM_VERSION}
PKGREVISION=	4
# The common runtime patch set also changes libunwind CMake checks.
EXTRACT_ELEMENTS+=	${DISTNAME}/libunwind
# One patch owner for native packages and the OS/SDK prepared source.
DISTINFO_FILE=	${.CURDIR}/distinfo
PATCHDIR=	${.CURDIR}/patches
PATCH_WRKSRC=	${WRKDIR}/${DISTNAME}
PATCH_STRIP=	-p1
PATCH_ARGS=	-d ${PATCH_WRKSRC} --forward --quiet -E ${PATCH_STRIP}

CATEGORIES=	lang devel

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://compiler-rt.llvm.org/
COMMENT=	LLVM runtime libraries
LICENSE=	apache-2.0

NOT_FOR_PLATFORM=	NetBSD-[0-7].*-*

USE_CC_FEATURES=	c99
USE_CXX_FEATURES=	c++17
USE_LANGUAGES=		c c++
USE_TOOLS+=		ggrep
GCC_REQD+=		16.2
SSP_SUPPORTED=		no

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DCOMPILER_RT_TEST_COMPILER=${PKG_CC:Q}
CMAKE_CONFIGURE_ARGS+=	-DCOMPILER_RT_OS_DIR:STRING=${OPSYS:tl}
CMAKE_CONFIGURE_ARGS+=	-DCOMPILER_RT_INSTALL_PATH:STRING=lib/clang/${LLVM_MAJOR_VERSION}
_COMPILER_RT_LLVM_PREFIX= ${BUILDLINK_PREFIX.llvm:U${LOCALBASE}}
CMAKE_CONFIGURE_ARGS+=	-DLLVM_CMAKE_DIR=${_COMPILER_RT_LLVM_PREFIX:Q}
CMAKE_CONFIGURE_ARGS+=	-DCOMPILER_RT_ENABLE_IOS=OFF

.include "../../mk/bsd.prefs.mk"
.include "../../mk/compiler.mk"
.include "../../lang/llvm/darwin.mk"

.if ${OPSYS} == "Darwin"
# Native macOS is the selected ABI; other Apple platforms are separate builds.
_COMPILER_RT_DARWIN_ARCH= ${MACHINE_ARCH:S/aarch64/arm64/}
CMAKE_CONFIGURE_ARGS+= -DDARWIN_macosx_CACHED_SYSROOT=${OSX_SDK_PATH:Q}
CMAKE_CONFIGURE_ARGS+= -DDARWIN_macosx_OVERRIDE_SDK_VERSION=${EMBERBSD_DARWIN_SDK_VERSION:Q}
CMAKE_CONFIGURE_ARGS+= -DDARWIN_osx_ARCHS=${_COMPILER_RT_DARWIN_ARCH:Q}
CMAKE_CONFIGURE_ARGS+= -DDARWIN_osx_BUILTIN_ARCHS=${_COMPILER_RT_DARWIN_ARCH:Q}
.if ${EMBERBSD_DARWIN_TOOL_PHASE:Ufull} == "initial"
# LLVM is already a dependency here, even while the compiler is bootstrapping.
# compiler-rt has its own UseLibtool module; bind its Darwin archiver explicitly.
CMAKE_CONFIGURE_ARGS+= -DCMAKE_LIBTOOL:FILEPATH=${_COMPILER_RT_LLVM_PREFIX:Q}/bin/llvm-libtool-darwin
.endif
CMAKE_CONFIGURE_ARGS+= -DCMAKE_LIPO=${_COMPILER_RT_LLVM_PREFIX:Q}/bin/llvm-lipo
CMAKE_CONFIGURE_ARGS+= -DCMAKE_INSTALL_NAME_TOOL=${_COMPILER_RT_LLVM_PREFIX:Q}/bin/llvm-install-name-tool
.for _apple_platform in IOS WATCHOS TVOS XROS
CMAKE_CONFIGURE_ARGS+= -DCOMPILER_RT_ENABLE_${_apple_platform}=OFF
.endfor
.if empty(OSX_SDK_PATH:M/*) || empty(EMBERBSD_DARWIN_SDK_VERSION)
PKG_FAIL_REASON+= "compiler-rt Darwin requires explicit OSX_SDK_PATH and EMBERBSD_DARWIN_SDK_VERSION"
.endif
.endif

# Not available to all platforms; see lib/tsan/rtl/tsan_platform_linux.cpp
# TODO: exclude more platforms
.if ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} != "x86_64"
CMAKE_CONFIGURE_ARGS+=	-DCOMPILER_RT_BUILD_SANITIZERS=OFF
.endif

TEST_TARGET=	check-compiler-rt

GENERATE_PLIST+=	${FIND} ${DESTDIR}${PREFIX} \( -type f -o -type l \) -print | \
			${SED} 's,${DESTDIR}${PREFIX}/,,' | ${SORT} ;

PYTHON_FOR_BUILD_ONLY=	yes

.if ${OPSYS} == "Darwin"
post-install:
	cd ${DESTDIR}${PREFIX} && \
	${FIND} lib/clang/${LLVM_MAJOR_VERSION} -type f -name '*.dylib' \
		-exec ${_COMPILER_RT_LLVM_PREFIX}/bin/llvm-install-name-tool -id ${PREFIX}/{} {} \;
.endif

.include "../../devel/cmake/build.mk"
.include "../../devel/googletest/buildlink3.mk"
.include "../../lang/llvm/buildlink3.mk"
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
