# Origin: EmberBSD contributors (AI-assisted).
V8_VERSION= 15.6.75.25
PKGREVISION= 6
V8_REVISION= 235050a0df6db2c9d92a419af2b72fbf3b2dd73b
DISTNAME= v8-${V8_VERSION}
PKGNAME= v8-source-${V8_VERSION}
CATEGORIES= lang
MASTER_SITES= ${MASTER_SITE_GITHUB:=v8/}
GITHUB_PROJECT= v8
GITHUB_TAG= ${V8_REVISION}
WRKSRC= ${WRKDIR}/v8-${V8_REVISION}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://v8.dev/
COMMENT= Shared V8 sources for runtime and browser builds
LICENSE= modified-bsd AND apache-2.0

NO_BUILD= yes
NO_CONFIGURE= yes
NO_ARCH= yes
USE_LANGUAGES= # source-only
USE_TOOLS+= find sort tar
PYTHON_FOR_BUILD_ONLY= tool
GENERATE_PLIST= cd ${DESTDIR:Q}${PREFIX:Q} && ${FIND} share/v8-source \( -type f -o -type l \) -print | ${SORT};
INSTALLATION_DIRS= share/v8-source

post-extract:
	${FIND} ${WRKSRC:Q} \( -name '*.orig' -o -name '*.rej' \) -print > ${WRKDIR:Q}/v8-original-backups
	${TEST} ! -s ${WRKDIR:Q}/v8-original-backups || { ${ECHO_MSG} "V8 archive contains patch backup names"; exit 1; }

do-install:
	${TAR} --exclude '*.orig' --exclude '*.rej' -cf ${WRKDIR:Q}/v8-source-copy.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/v8-source-copy.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/v8-source
	${PYTHONBIN:Q} ${FILESDIR:Q}/stamp-source.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} \
	    --source ${DESTDIR:Q}${PREFIX:Q}/share/v8-source --pkgsrc-root ${PKGSRCDIR:Q}

.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
