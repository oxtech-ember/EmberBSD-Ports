# $NetBSD: Makefile,v 1.116 2026/09/16 11:00:39 tnn Exp $
#
# When updating this, please also update:
# devel/include-what-you-use
# devel/lld
# devel/lldb
# devel/polly
# lang/clang
# lang/clang-tools-extra
# lang/compiler-rt
# lang/libcxx
# lang/libcxxabi
# lang/libunwind
# lang/wasi-compiler-rt
# lang/wasi-libcxx
# parallel/openmp
#
# Do not update:
#   lang/libLLVM
# because pkgsrc provides multiple versions and lang/libLLVM is
# logically libLLVM4.
#
# Always update all */buildlink3.mk to require the latest stable release
# version in BUILDLINK_API_DEPENDS, as there is no backwards compatibility.

EMBERBSD_LLVM_PKGDIR:= ${.PARSEDIR:tA}
.include "version.mk"

PKGNAME=	llvm-${LLVM_VERSION}
CATEGORIES=	lang devel

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://llvm.org/
COMMENT=	Low Level Virtual Machine compiler infrastructure
LICENSE=	apache-2.0

POLICY_UPDATE_LIMITED=	abi

USE_CXX_FEATURES=	c++17 charconv
USE_LANGUAGES=		c c++
GCC_REQD+=		16.2
PYTHON_FOR_BUILD_ONLY=	no

NOT_FOR_PLATFORM+=	*-*-alpha
NOT_FOR_PLATFORM+=	*-*-vax

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_CXX_LINK_FLAGS:STRING=${LDFLAGS:Q}
CMAKE_CONFIGURE_ARGS+=	-DLLVM_BUILD_LLVM_DYLIB=ON
CMAKE_CONFIGURE_ARGS+=	-DLLVM_INCLUDE_BENCHMARKS=OFF
CMAKE_CONFIGURE_ARGS+=	-DLLVM_INSTALL_UTILS=ON
CMAKE_CONFIGURE_ARGS+=	-DLLVM_LINK_LLVM_DYLIB=ON
CMAKE_CONFIGURE_ARGS+=	-DLLVM_ENABLE_RTTI=ON
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=OFF
CMAKE_CONFIGURE_ARGS+=	-DLLVM_ENABLE_LIBCXX=OFF
CMAKE_CONFIGURE_ARGS+=	-DLLVM_INSTALL_TOOLCHAIN_ONLY=OFF
CMAKE_CONFIGURE_ARGS+=	-DLLVM_BUILD_RUNTIME=OFF
CMAKE_CONFIGURE_ARGS+=	-DLLVM_INCLUDE_RUNTIMES=OFF
CMAKE_CONFIGURE_ARGS+=	-DPython3_EXECUTABLE=${TOOL_PYTHONBIN:Q}

CMAKE_CONFIGURE_ARGS.Darwin+=	-DCMAKE_LIBTOOL=/usr/bin/libtool

CHECK_PORTABILITY_SKIP=	utils/buildit/build_llvm

# XXX perl is not added as a tool as it does not seem to be required
REPLACE_PERL+=		utils/*.pl
REPLACE_PERL+=		utils/codegen-diff
REPLACE_PERL+=		utils/llvm-native-gxx

REPLACE_PYTHON+=	tools/opt-viewer/*.py
REPLACE_PYTHON+=	tools/sancov/*.py
REPLACE_PYTHON+=	utils/*.py
REPLACE_PYTHON+=	utils/Misc/zkill
REPLACE_PYTHON+=	utils/bisect
REPLACE_PYTHON+=	utils/clang-parse-diagnostics-file
REPLACE_PYTHON+=	utils/lit/tests/Inputs/googletest-format/DummySubDir/OneTest.py

TEST_TARGET=		check
TEST_ENV+=		LD_LIBRARY_PATH=${WRKDIR}/build/lib

# It may be that the Solaris linker is more strict here and they can be removed on
# all platforms.  Change this to a patch if verified.
SUBST_CLASSES.SunOS+=	linkmap
SUBST_STAGE.linkmap=	pre-configure
SUBST_FILES.linkmap+=	tools/remarks-shlib/Remarks.exports
SUBST_SED.linkmap=	-e '/^LLVM/d'

LDFLAGS.SunOS+=		-lsocket -lnsl

.include "../../mk/bsd.prefs.mk"

.if defined(EMBERBSD_LLVM_DEVEL)
.if ${EMBERBSD_LLVM_DEVEL} != "yes" || ${PKGPATH} != "lang/llvm-devel"
PKG_FAIL_REASON+= "The LLVM SDK role belongs to lang/llvm-devel"
.endif
PKGNAME= llvm-devel-${LLVM_VERSION}
COMMENT= LLVM target SDK for the development-host sysroot
DISTINFO_FILE= ${EMBERBSD_LLVM_PKGDIR}/distinfo
PATCHDIR= ${EMBERBSD_LLVM_PKGDIR}/patches
FILESDIR= ${EMBERBSD_LLVM_PKGDIR}/files
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD"
PKG_FAIL_REASON+= "The separate LLVM SDK requires a NetBSD cross build; native LLVM retains its full package"
.endif
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
.if ${MACHINE_ARCH} != "aarch64" && ${MACHINE_ARCH} != "x86_64"
PKG_FAIL_REASON+= "The LLVM runtime/SDK split requires the common aarch64 or amd64 cross target"
.endif
.if defined(EMBERBSD_LLVM_DEVEL)
PKGREVISION= 2
.if ${PKGREVISION} != 2
PKG_FAIL_REASON+= "The LLVM SDK requires package revision 2"
.endif
.else
PKGREVISION= 1
.if ${PKGREVISION} != 1
PKG_FAIL_REASON+= "The LLVM runtime requires package revision 1"
.endif
.endif
# Both partitions come from the same full build with native Python tools.
PYTHON_FOR_BUILD_ONLY= tool
# lit supplies build/test scripts, not target library search paths.
BUILDLINK_DEPMETHOD.py-llvm-lit= build
LLVM_FULL_PLIST_SRC= ${EMBERBSD_LLVM_PKGDIR}/PLIST
LLVM_RUNTIME_PLIST_SRC= ${EMBERBSD_LLVM_PKGDIR}/PLIST.runtime
LLVM_DEVEL_PLIST_SRC= ${EMBERBSD_LLVM_PKGDIR}/../llvm-devel/PLIST
.if defined(EMBERBSD_LLVM_DEVEL)
LLVM_PACKAGE_PART= devel
# The installed scripts need Python, but LLVM does not link its C API.
DEPENDS+= ${PYDEPENDENCY}
.if ${LLVM_PACKAGE_PART} != "devel"
PKG_FAIL_REASON+= "The LLVM SDK recipe must select the devel partition"
.endif
PLIST_SRC= ${LLVM_DEVEL_PLIST_SRC}
DEPENDS+= llvm-${LLVM_VERSION}nb1:../../lang/llvm
CONFLICTS+= llvm<${LLVM_VERSION}nb1
.else
LLVM_PACKAGE_PART= runtime
.if ${LLVM_PACKAGE_PART} != "runtime"
PKG_FAIL_REASON+= "The LLVM runtime recipe must select the runtime partition"
.endif
PLIST_SRC= ${LLVM_RUNTIME_PLIST_SRC}
.endif
USE_TOOLS+= perl:build
.endif

.if ${USE_CROSS_COMPILE:tl} == "yes"
# Fix the runtime Python path.
SUBST_CLASSES+=		python
SUBST_STAGE.python=	post-build
SUBST_FILES.python=	${CMAKE_BUILD_DIR}/bin/llvm-lit
SUBST_SED.python=	-e '1s,\#!.*python.*,\#!${PYTHONBIN},'
.endif

PLIST_VARS+=	darwin notdylib
.if ${OPSYS} == "Darwin"
PLIST.darwin=	yes
.endif
.if ${SHLIB_TYPE} != "dylib"
PLIST.notdylib=	yes
.endif

NOTDYLIBS=		LTO Remarks
.for libname in ${NOTDYLIBS}
PRINT_PLIST_AWK+=	/lib${libname}.${SHLIB_EXT}.${LLVM_MAJOR_VERSION}/ { gsub(/\.${SHLIB_EXT}\.${LLVM_MAJOR_VERSION}/, ".$${SHLIB_EXT}.$${LLVM_MAJOR_VERSION}"); print "$${PLIST.notdylib}" $$0; next }
.endfor
PRINT_PLIST_AWK+=	{ gsub(/\.${SHLIB_EXT}/, ".$${SHLIB_EXT}") }

# needs std::atomic with 64-bit CAS
.if ${MACHINE_ARCH} == "i386"
CXXFLAGS+=	-march=i586
.endif

.if ${MACHINE_ARCH:Mpowerpc*}
# Needed to avoid "relocation truncated to fit: R_PPC_REL24"
CFLAGS+=	-mlongcall
CXXFLAGS+=	-mlongcall
.  if ${OPSYS} == "NetBSD"
.    if ${OPSYS_VERSION} >= 099917
# The -mno-pltseq option is not available in gcc7, but is needed for
# the above-mentioned relocation truncation issue in newer GCC
CFLAGS+=	-mno-pltseq
CXXFLAGS+=	-mno-pltseq
.    endif # (just drop for older NetBSD)
.  else # Not NetBSD
# Let's just insist on newer gcc -- untested.
CFLAGS+=	-mno-pltseq
CXXFLAGS+=	-mno-pltseq
.  endif
.endif

PLIST_SUBST+=	RELEASE_TYPE=${RELEASE_TYPE}

.if ${OPSYS} == "NetBSD"
CMAKE_CONFIGURE_ARGS+=	-DPKGSRC_LLVM_PTHREADLIB=-lpthread
.endif

.if ${USE_CROSS_COMPILE:U:tl} == "yes"
.if defined(EMBERBSD_LLVM_NATIVE_TOOLS)
.include "cross.mk"
.else
TOOL_DEPENDS+=		llvm-${LLVM_VERSION}{,nb*}:../../lang/llvm
CMAKE_CONFIGURE_ARGS+=	-DLLVM_TABLEGEN:STRING=${TOOLBASE:Q}/bin/llvm-tblgen
.endif
.endif

.include "options.mk"

.include "../../devel/py-llvm-lit/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD" || defined(EMBERBSD_LLVM_DEVEL)
DEPENDS+= ${PYPKGPREFIX}-llvm-lit-${LLVM_VERSION}{,nb*}:../../devel/py-llvm-lit
.endif

.include "reuse.mk"

.if !defined(_EMBERBSD_LLVM_REUSE)
# replacing config.guess is required even for cmake.
# It is used to detect correct LLVM_HOST_TRIPLE, e.g. for NetBSD/evbarm.
post-extract:
.for f in config.guess config.sub
	${CP} ../../mk/gnu-config/${f} ${WRKSRC}/cmake/${f}
.endfor

.endif

.include "../../devel/cmake/build.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../lang/python/tool.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
# Stage the full LLVM payload before selecting the package partition.
post-install: llvm-select-stage
.PHONY: llvm-select-stage
.PHONY: ${WRKDIR}/.llvm-full-plist ${WRKDIR}/.llvm-runtime-plist ${WRKDIR}/.llvm-devel-plist
llvm-select-stage: ${PLIST}
.for _llvm_part in FULL RUNTIME DEVEL
	${MAKE} ${WRKDIR:Q}/.llvm-${_llvm_part:tl}-plist \
	    PLIST=${WRKDIR:Q}/.llvm-${_llvm_part:tl}-plist \
	    PLIST_SRC=${LLVM_${_llvm_part}_PLIST_SRC:Q}
.endfor
	${TOOL_PYTHONBIN} -B ${FILESDIR}/select-package-stage.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} ${LLVM_PACKAGE_PART:Q} \
	    ${DESTDIR:Q}${PREFIX:Q} ${WRKDIR:Q}/.llvm-full-plist \
	    ${WRKDIR:Q}/.llvm-runtime-plist ${WRKDIR:Q}/.llvm-devel-plist ${PLIST:Q}
.endif
