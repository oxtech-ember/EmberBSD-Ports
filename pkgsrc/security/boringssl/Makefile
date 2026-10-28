# Origin: EmberBSD (AI-assisted). Shared BoringSSL source and patch owner.
DISTNAME= boringssl-0.0.0pre20261028
CATEGORIES= security
BORINGSSL_REVISION= df870ed7fa51110edb872beb3357a44d20e1ce56
BORINGSSL_TREE= f07af48aecdfee27c1b7e78490be48a287b3f6a9
DISTFILES= ${DISTNAME}.tar
EXTRACT_SUFX= .tar
HOMEPAGE= https://boringssl.googlesource.com/boringssl/
COMMENT= Shared BoringSSL source for native and target consumers
LICENSE= apache-2.0 AND modified-bsd
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source-only package
USE_TOOLS+= find sort tar
PYTHON_FOR_BUILD_ONLY= tool
BUILD_DEFS+= EMBERBSD_SDK_SOURCE
BORINGSSL_FETCH_PYTHON?= ${TOOL_PYTHONBIN}

do-fetch: error-check
	${RUN} set -e; \
	if ${TEST} ! -f ${DISTDIR:Q}/${DISTFILES:Q}; then \
	    case x${BORINGSSL_FETCH_PYTHON:Q} in x/*) ;; *) ${FAIL_MSG} "Select absolute BORINGSSL_FETCH_PYTHON" ;; esac; \
	    case x${EMBERBSD_SDK_SOURCE:Q} in x/*) ;; *) ${FAIL_MSG} "Set EMBERBSD_SDK_SOURCE to SDK source code" ;; esac; \
	    ${BORINGSSL_FETCH_PYTHON:Q} -B -I -S ${FILESDIR:Q}/fetch-source.py \
	        --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --revision ${BORINGSSL_REVISION:Q} \
	        --tree ${BORINGSSL_TREE:Q} --root-name ${DISTNAME:Q} \
	        --output ${DISTDIR:Q}/${DISTFILES:Q}; \
	fi

post-extract:
	${FIND} ${WRKSRC:Q} \( -name '*.orig' -o -name '*.rej' \) -print > ${WRKDIR:Q}/boringssl-original-backups
	${TEST} ! -s ${WRKDIR:Q}/boringssl-original-backups || { ${ECHO_MSG} "Archive contains patch backup names"; exit 1; }

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/boringssl-source
	${TAR} --exclude '*.orig' --exclude '*.rej' -cf ${WRKDIR:Q}/boringssl-source-copy.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/boringssl-source-copy.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/boringssl-source
	${TOOL_PYTHONBIN:Q} -B -I -S ${FILESDIR:Q}/stamp-source.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} \
	    --source ${DESTDIR:Q}${PREFIX:Q}/share/boringssl-source --pkgsrc-root ${_PKGSRCDIR:Q}

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/boringssl-source \( -type f -o -type l \) -print | ${SORT};
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
