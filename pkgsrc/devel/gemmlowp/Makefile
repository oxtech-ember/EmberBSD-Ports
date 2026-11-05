# Origin: EmberBSD contributors (AI-assisted); upstream shared source owner.
DISTNAME= gemmlowp-16e8662c34917be0065110bfcd9cc27d30f52fdf
PKGNAME= gemmlowp-source-0.0.20231103
CATEGORIES= devel
MASTER_SITES= -https://github.com/google/gemmlowp/archive/16e8662c34917be0065110bfcd9cc27d30f52fdf.tar.gz
WRKSRC= ${WRKDIR}/gemmlowp-16e8662c34917be0065110bfcd9cc27d30f52fdf
HOMEPAGE= https://github.com/google/gemmlowp
COMMENT= Shared gemmlowp upstream source for SDK consumers
LICENSE= apache-2.0
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar
CHECK_INTERPRETER_SKIP+= share/gemmlowp-source/*

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/gemmlowp-source
	${TAR} -cf ${WRKDIR:Q}/gemmlowp-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/gemmlowp-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/gemmlowp-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/gemmlowp-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
