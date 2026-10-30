# Origin: EmberBSD (AI-assisted). Source is prepared by the common LLVM runtime owner.
.include "../../lang/llvm/version.mk"
PKGNAME= llvm-libc-source-${LLVM_VERSION}
CATEGORIES= lang devel
COMMENT= Shared LLVM libc source for consumers of its support headers
HOMEPAGE= https://libc.llvm.org/
LICENSE= apache-2.0
NO_ARCH= yes
NO_CONFIGURE= yes
EXTRACT_ONLY=
WRKSRC= ${WRKDIR}
DISTINFO_FILE= ${.CURDIR}/../../lang/llvm/distinfo
USE_LANGUAGES= # source-only package
USE_TOOLS+= find sort
PYTHON_FOR_BUILD_ONLY= tool
TOOL_DEPENDS+= patch-[0-9]*:../../devel/patch
EMBERBSD_LLVM_LIBC_HOST_PREFIX?= ${TOOLBASE}
BUILD_DEFS+= EMBERBSD_SDK_SOURCE EMBERBSD_LLVM_LIBC_HOST_PREFIX
_LLVM_RUNTIME_OWNER= ${_PKGSRCDIR}/lang/compiler-rt/files/runtime.py
_LLVM_RUNTIME_SOURCE= ${WRKDIR}/llvm-runtime-source
_LLVM_LIBC_DEST= ${DESTDIR}${PREFIX}/share/llvm-libc-source

do-build:
	${RUN} case x${EMBERBSD_LLVM_LIBC_HOST_PREFIX:Q} in x/*) ;; *) ${FAIL_MSG} "Select absolute EMBERBSD_LLVM_LIBC_HOST_PREFIX" ;; esac
	${TOOL_PYTHONBIN:Q} -B -I -S ${_LLVM_RUNTIME_OWNER:Q} --sdk-source ${EMBERBSD_SDK_SOURCE:Q} \
	    --pkgsrc-root ${_PKGSRCDIR:Q} prepare --archive ${DISTDIR:Q}/${DISTNAME:Q}${EXTRACT_SUFX:Q} \
	    --source ${_LLVM_RUNTIME_SOURCE:Q} --patch ${EMBERBSD_LLVM_LIBC_HOST_PREFIX:Q}/bin/gpatch

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share
	${CP} -R ${_LLVM_RUNTIME_SOURCE:Q}/libc ${_LLVM_LIBC_DEST:Q}
	${TOOL_PYTHONBIN:Q} -B -I -S ${FILESDIR:Q}/stamp-source.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} \
	    --runtime-source ${_LLVM_RUNTIME_SOURCE:Q} --source ${_LLVM_LIBC_DEST:Q}

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/llvm-libc-source \( -type f -o -type l \) -print | ${SORT};
# The payload is source for consumers that run its scripts with their own
# selected interpreters; nothing executes it from ${PREFIX}. pkgsrc skips
# share/doc and share/examples for the same reason.
CHECK_INTERPRETER_SKIP+= share/llvm-libc-source/*
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
