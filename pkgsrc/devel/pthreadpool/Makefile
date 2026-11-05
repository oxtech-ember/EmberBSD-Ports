# Origin: EmberBSD contributors (AI-assisted); upstream shared source owner.
DISTNAME= pthreadpool-15a6644ba1c45f1acc16ac1e883efc3e56c6bed2
PKGNAME= pthreadpool-source-0.0.20260909
CATEGORIES= devel
MASTER_SITES= -https://github.com/google/pthreadpool/archive/15a6644ba1c45f1acc16ac1e883efc3e56c6bed2.tar.gz
WRKSRC= ${WRKDIR}/pthreadpool-15a6644ba1c45f1acc16ac1e883efc3e56c6bed2
HOMEPAGE= https://github.com/google/pthreadpool
COMMENT= Shared pthreadpool upstream source for SDK consumers
LICENSE= 2-clause-bsd
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar
CHECK_INTERPRETER_SKIP+= share/pthreadpool-source/*

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/pthreadpool-source
	${TAR} -cf ${WRKDIR:Q}/pthreadpool-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/pthreadpool-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/pthreadpool-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/pthreadpool-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
