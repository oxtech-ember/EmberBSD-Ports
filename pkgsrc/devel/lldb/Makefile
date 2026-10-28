# $NetBSD: Makefile,v 1.65 2026/09/02 19:01:39 wiz Exp $

PKGREVISION= 2
.include "../../lang/llvm/version.mk"

PKGNAME=	lldb-${LLVM_VERSION}
CATEGORIES=	devel lang

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	http://lldb.org/
COMMENT=	Next generation, high-performance debugger
LICENSE=	apache-2.0

DEPENDS+=	llvm-${PKGVERSION_NOREV}{,nb*}:../../lang/llvm
DEPENDS+=	clang-${PKGVERSION_NOREV}{,nb*}:../../lang/clang
TOOL_DEPENDS+=	swig4>=4.5.1:../../devel/swig4
DEPENDS+=	${PYPKGPREFIX}-six-[0-9]*:../../lang/py-six

USE_CXX_FEATURES=	c++17
USE_LANGUAGES=		c c++
GCC_REQD+=		7
PY_PATCHPLIST=		yes

# FIXME: currently build fails when libcxx is also installed.
CMAKE_CONFIGURE_ARGS+=	-DLLVM_CONFIG=${LLVM_CONFIG_PATH:Q}
CMAKE_CONFIGURE_ARGS+=	-DSWIG_EXECUTABLE=${TOOLBASE:Q}/bin/swig4.0
#CMAKE_CONFIGURE_ARGS+=	-DLLVM_ENABLE_LIBCXX=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_C_COMPILER=${CC:Q}
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_CXX_COMPILER=${CXX:Q}
CMAKE_CONFIGURE_ARGS+=	-DHAVE_CXX_ATOMICS64_WITHOUT_LIB=ON
CMAKE_CONFIGURE_ARGS+=	-DLLDB_CODESIGN_IDENTITY=""
CMAKE_CONFIGURE_ARGS+=	-DPYTHON_HOME=${PREFIX}

CHECK_PORTABILITY_SKIP=	utils/buildit/build_llvm

LUA_VERSIONS_ACCEPTED=	55
PLIST_SUBST+=		LUA_VERSION=${LUA_VERSION:R}
PLIST_SUBST+=		LLDB_SHLIB_VERSION=${LLVM_VERSION:R}

REPLACE_PERL+=		scripts/disasm-gdb-remote.pl

REPLACE_PYTHON+=	bindings/python/get-python-config.py
REPLACE_PYTHON+=	bindings/python/lldb-python
REPLACE_PYTHON+=	scripts/analyze-project-deps.py
REPLACE_PYTHON+=	scripts/generate-sbapi-dwarf-enum.py
REPLACE_PYTHON+=	scripts/verify_api.py
REPLACE_PYTHON+=	utils/lui/lui.py
REPLACE_PYTHON+=	utils/lui/sandbox.py

TEST_TARGET=		check-lldb
#TEST_TARGET=		check-lldb-unit # doesn't work in standalone build
#TEST_TARGET=		check-lldb-single # check-lldb -j1
#TEST_TARGET=		check-lldb-expr # unknown
TEST_ENV+=		LD_LIBRARY_PATH=${WRKDIR}/build/lib

.include "../../mk/bsd.prefs.mk"

.if ${OPSYS} == "Darwin"
TOOL_DEPENDS+= mig>=138:../../devel/mig
.if ${NATIVE_OPSYS} == "Darwin"
TOOL_DEPENDS+= cctools-codesign-allocate>=1030.6.3:../../devel/cctools
CMAKE_CONFIGURE_ARGS+= -DCMAKE_CODESIGN=/usr/bin/codesign
CMAKE_CONFIGURE_ARGS+= -DCMAKE_CODESIGN_ALLOCATE=${TOOLBASE:Q}/bin/codesign_allocate
.endif
MAKE_ENV+= MIGCC=${CC:Q}
MAKE_ENV+= MIGCOM=${TOOLBASE:Q}/libexec/migcom
MAKE_ENV+= SDKROOT=${OSX_SDK_PATH:Q}
.endif

.include "options.mk"

.if ${OPSYS} == "NetBSD"
.  if ${OPSYS_VERSION} < 99922
# lacks ptrace(2) PT_STOP
PKG_FAIL_REASON+=	"Only NetBSD >= 9.99.22 provides ptrace(2) PT_STOP"
.  endif
.endif

# Not yet ported, so avoid wasting time trying...
# See: source/Plugins/Process/NetBSD
NOT_FOR_PLATFORM+=	NetBSD-*-aarch64 NetBSD-*-powerpc

# Makefile generators cannot resolve dynamic interpreter export dependencies.
CMAKE_GENERATORS_INCOMPATIBLE+= make

.include "../../devel/cmake/build.mk"
#.include "../../devel/googletest/buildlink3.mk" # check-lldb-unit
.include "../../devel/editline/buildlink3.mk"
.include "../../devel/swig4/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../lang/clang/buildlink3.mk"
#.include "../../lang/libcxx/buildlink3.mk"
.include "../../lang/llvm/buildlink3.mk"
.include "../../lang/lua/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../lang/python/extension.mk"
.include "../../lang/python/tool.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
