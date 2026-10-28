# Origin: EmberBSD (AI-assisted), Chromium inspector protocol source.
DISTNAME= inspector-protocol-0.0.0pre20261020
CATEGORIES= devel
INSPECTOR_REVISION= 3f95e5ac93fab4a064e637b3567f63b9007d9937
INSPECTOR_TREE= 4df18a260c2baac122c176713b5696178000d629
DISTFILES= ${DISTNAME}.tar
EXTRACT_SUFX= .tar
HOMEPAGE= https://chromium.googlesource.com/deps/inspector_protocol/
COMMENT= Shared inspector protocol and CRDTP sources
LICENSE= modified-bsd
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source-only package
USE_TOOLS+= find sort tar
PYTHON_FOR_BUILD_ONLY= tool
BUILD_DEFS+= EMBERBSD_SDK_SOURCE
INSPECTOR_FETCH_PYTHON?= ${TOOL_PYTHONBIN}

do-fetch: error-check
	${RUN} set -e; \
	if ${TEST} ! -f ${DISTDIR:Q}/${DISTFILES:Q}; then \
	    case x${INSPECTOR_FETCH_PYTHON:Q} in x/*) ;; *) ${FAIL_MSG} "Select absolute INSPECTOR_FETCH_PYTHON" ;; esac; \
	    case x${EMBERBSD_SDK_SOURCE:Q} in x/*) ;; *) ${FAIL_MSG} "Set EMBERBSD_SDK_SOURCE to SDK source code" ;; esac; \
	    ${INSPECTOR_FETCH_PYTHON:Q} -B -I -S ${FILESDIR:Q}/fetch-source.py \
	        --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --revision ${INSPECTOR_REVISION:Q} \
	        --tree ${INSPECTOR_TREE:Q} --root-name ${DISTNAME:Q} \
	        --output ${DISTDIR:Q}/${DISTFILES:Q}; \
	fi

post-extract:
	${FIND} ${WRKSRC:Q} \( -name '*.orig' -o -name '*.rej' \) -print > ${WRKDIR:Q}/inspector-original-backups
	${TEST} ! -s ${WRKDIR:Q}/inspector-original-backups || { ${ECHO_MSG} "Archive contains patch backup names"; exit 1; }

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/inspector-protocol
	${TAR} --exclude '*.orig' --exclude '*.rej' -cf ${WRKDIR:Q}/inspector-source-copy.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/inspector-source-copy.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/inspector-protocol
	${TOOL_PYTHONBIN} -B -I -S ${FILESDIR:Q}/stamp-source.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} \
	    --source ${DESTDIR:Q}${PREFIX:Q}/share/inspector-protocol --pkgsrc-root ${_PKGSRCDIR:Q}

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/inspector-protocol \( -type f -o -type l \) -print | ${SORT};
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
