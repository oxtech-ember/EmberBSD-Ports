# Origin: EmberBSD (AI-assisted); common compiler-rt source and WASI producer.
.include "../../lang/llvm/version.mk"

PKGNAME= wasi-compiler-rt-${LLVM_VERSION}
PKGREVISION= 1
NO_ARCH= yes
CATEGORIES= lang devel
HOMEPAGE= https://compiler-rt.llvm.org/
COMMENT= LLVM compiler-rt builtins for the WASI preview1 ABI
LICENSE= apache-2.0
DISTINFO_FILE= ${.CURDIR}/../../lang/compiler-rt/distinfo
EXTRACT_ONLY=
NO_CONFIGURE= yes
WRKSRC= ${WRKDIR}
USE_LANGUAGES= c c++
PYTHON_FOR_BUILD_ONLY= tool
TOOL_DEPENDS+= cmake-[0-9]*:../../devel/cmake
TOOL_DEPENDS+= ninja-build-[0-9]*:../../devel/ninja-build
TOOL_DEPENDS+= patch-[0-9]*:../../devel/patch
TOOL_DEPENDS+= clang-${LLVM_VERSION}*:../../lang/clang
TOOL_DEPENDS+= llvm-${LLVM_VERSION}*:../../lang/llvm
TOOL_DEPENDS+= lld-${LLVM_VERSION}*:../../devel/lld

EMBERBSD_WASI_HOST_PREFIX?= ${TOOLBASE}
BUILD_DEFS+= EMBERBSD_SDK_SOURCE EMBERBSD_WASI_HOST_PREFIX
.if empty(EMBERBSD_SDK_SOURCE:M/*) || empty(EMBERBSD_WASI_HOST_PREFIX:M/*)
PKG_FAIL_REASON+= "Select EMBERBSD_SDK_SOURCE and EMBERBSD_WASI_HOST_PREFIX as absolute paths."
.endif
_WASI_OWNER= ${.CURDIR}/../../lang/compiler-rt/files/runtime.py
_WASI_PY= ${TOOL_PYTHONBIN} -B -S ${_WASI_OWNER:Q} --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --pkgsrc-root ${_PKGSRCDIR:Q}
_WASI_SOURCE= ${WRKDIR}/common-runtime-source
_WASI_WORK= ${WRKDIR}/wasi-builtins-work
_WASI_STAGE= ${WRKDIR}/wasi-builtins-stage
_WASI_RESOURCE= ${PREFIX}/lib/clang/${LLVM_MAJOR_VERSION}

INSTALLATION_DIRS+= lib/clang/${LLVM_MAJOR_VERSION} share/licenses/wasi-compiler-rt

do-build:
	${_WASI_PY} prepare --archive ${DISTDIR:Q}/${DISTNAME:Q}${EXTRACT_SUFX:Q} \
	    --source ${_WASI_SOURCE:Q} --patch ${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/gpatch
	${_WASI_PY} wasi-builtins --source ${_WASI_SOURCE:Q} \
	    --host-prefix ${EMBERBSD_WASI_HOST_PREFIX:Q} --work ${_WASI_WORK:Q} \
	    --stage ${_WASI_STAGE:Q} --jobs ${MAKE_JOBS:U1}

do-install:
	${CP} -R ${_WASI_STAGE:Q}/lib ${DESTDIR:Q}${_WASI_RESOURCE:Q}/
	${LN} -s wasm32-unknown-wasip1 ${DESTDIR:Q}${_WASI_RESOURCE:Q}/lib/wasm32-unknown-wasi
	${INSTALL_DATA} ${_WASI_STAGE:Q}/share/licenses/compiler-rt/* \
	    ${DESTDIR:Q}${PREFIX:Q}/share/licenses/wasi-compiler-rt/

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} lib/clang/${LLVM_MAJOR_VERSION}/lib/wasm32-unknown-wasi* share/licenses/wasi-compiler-rt \( -type f -o -type l \) -print | ${SORT};

.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
