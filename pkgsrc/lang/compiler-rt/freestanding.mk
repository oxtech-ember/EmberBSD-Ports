# Origin: EmberBSD (AI-assisted); shared freestanding compiler-rt package machinery.
.include "../../lang/llvm/version.mk"

PKGNAME= ${FREESTANDING_PACKAGE}-${LLVM_VERSION}
NO_ARCH= yes
CATEGORIES= lang devel
HOMEPAGE= https://compiler-rt.llvm.org/
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

EMBERBSD_FREESTANDING_HOST_PREFIX?= ${TOOLBASE}
BUILD_DEFS+= EMBERBSD_SDK_SOURCE EMBERBSD_FREESTANDING_HOST_PREFIX
.if empty(EMBERBSD_SDK_SOURCE:M/*) || empty(EMBERBSD_FREESTANDING_HOST_PREFIX:M/*)
PKG_FAIL_REASON+= "Select EMBERBSD_SDK_SOURCE and EMBERBSD_FREESTANDING_HOST_PREFIX as absolute paths."
.endif
_FREESTANDING_OWNER= ${.CURDIR}/../../lang/compiler-rt/files/runtime.py
_FREESTANDING_PY= ${TOOL_PYTHONBIN} -B -S ${_FREESTANDING_OWNER:Q} --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --pkgsrc-root ${_PKGSRCDIR:Q}
_FREESTANDING_SOURCE= ${WRKDIR}/common-runtime-source
_FREESTANDING_WORK= ${WRKDIR}/freestanding-builtins-work
_FREESTANDING_STAGE= ${WRKDIR}/freestanding-builtins-stage
_FREESTANDING_RESOURCE= ${PREFIX}/lib/clang/${LLVM_MAJOR_VERSION}

INSTALLATION_DIRS+= lib/clang/${LLVM_MAJOR_VERSION} share/licenses/${FREESTANDING_PACKAGE}

do-build:
	${_FREESTANDING_PY} prepare --archive ${DISTDIR:Q}/${DISTNAME:Q}${EXTRACT_SUFX:Q} \
	    --source ${_FREESTANDING_SOURCE:Q} --patch ${EMBERBSD_FREESTANDING_HOST_PREFIX:Q}/bin/gpatch
	${_FREESTANDING_PY} freestanding-builtins --target ${FREESTANDING_TARGET:Q} --source ${_FREESTANDING_SOURCE:Q} \
	    --host-prefix ${EMBERBSD_FREESTANDING_HOST_PREFIX:Q} --work ${_FREESTANDING_WORK:Q} \
	    --stage ${_FREESTANDING_STAGE:Q} --jobs ${MAKE_JOBS:U1}

do-install:
	${CP} -R ${_FREESTANDING_STAGE:Q}/lib ${DESTDIR:Q}${_FREESTANDING_RESOURCE:Q}/
.if defined(FREESTANDING_RESOURCE_ALIAS)
	${LN} -s ${FREESTANDING_RESOURCE_DIR:Q} ${DESTDIR:Q}${_FREESTANDING_RESOURCE:Q}/lib/${FREESTANDING_RESOURCE_ALIAS:Q}
.endif
	${INSTALL_DATA} ${_FREESTANDING_STAGE:Q}/share/licenses/compiler-rt/* \
	    ${DESTDIR:Q}${PREFIX:Q}/share/licenses/${FREESTANDING_PACKAGE}/

_FREESTANDING_PLIST= lib/clang/${LLVM_MAJOR_VERSION}/lib/${FREESTANDING_RESOURCE_DIR} share/licenses/${FREESTANDING_PACKAGE}
.if defined(FREESTANDING_RESOURCE_ALIAS)
_FREESTANDING_PLIST+= lib/clang/${LLVM_MAJOR_VERSION}/lib/${FREESTANDING_RESOURCE_ALIAS}
.endif
GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} ${_FREESTANDING_PLIST} \( -type f -o -type l \) -print | ${SORT};

.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
