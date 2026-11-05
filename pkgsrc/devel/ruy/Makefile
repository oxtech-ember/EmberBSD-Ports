# Origin: EmberBSD contributors (AI-assisted); upstream shared source owner.
DISTNAME= ruy-2264753777198e4393fb83c44c693462d57a2be1
PKGNAME= ruy-source-0.0.20260722
CATEGORIES= devel
MASTER_SITES= -https://github.com/google/ruy/archive/2264753777198e4393fb83c44c693462d57a2be1.tar.gz
WRKSRC= ${WRKDIR}/ruy-2264753777198e4393fb83c44c693462d57a2be1
HOMEPAGE= https://github.com/google/ruy
COMMENT= Shared ruy upstream source for SDK consumers
LICENSE= apache-2.0
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar
CHECK_INTERPRETER_SKIP+= share/ruy-source/*

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/ruy-source
	${TAR} -cf ${WRKDIR:Q}/ruy-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/ruy-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/ruy-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/ruy-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
