# Origin: EmberBSD contributors (AI-assisted); upstream shared source owner.
DISTNAME= farmhash-9d99331eb762e9ee22fd97d15a594525ad98310a
PKGNAME= farmhash-source-0.0.20260605
CATEGORIES= devel
MASTER_SITES= -https://github.com/google/farmhash/archive/9d99331eb762e9ee22fd97d15a594525ad98310a.tar.gz
WRKSRC= ${WRKDIR}/farmhash-9d99331eb762e9ee22fd97d15a594525ad98310a
HOMEPAGE= https://github.com/google/farmhash
COMMENT= Shared farmhash upstream source for SDK consumers
LICENSE= mit
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar
CHECK_INTERPRETER_SKIP+= share/farmhash-source/*

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/farmhash-source
	${TAR} -cf ${WRKDIR:Q}/farmhash-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/farmhash-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/farmhash-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/farmhash-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
