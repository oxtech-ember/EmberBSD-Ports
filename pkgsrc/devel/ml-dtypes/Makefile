# Origin: EmberBSD contributors (AI-assisted); upstream shared source owner.
DISTNAME= ml-dtypes-0.6.0
PKGNAME= ml-dtypes-source-0.6.0
CATEGORIES= devel
MASTER_SITES= -https://github.com/jax-ml/ml_dtypes/archive/v0.6.0.tar.gz
WRKSRC= ${WRKDIR}/ml_dtypes-0.6.0
HOMEPAGE= https://github.com/jax-ml/ml_dtypes
COMMENT= Shared ml-dtypes upstream source for SDK consumers
LICENSE= apache-2.0
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar
CHECK_INTERPRETER_SKIP+= share/ml-dtypes-source/*

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/ml-dtypes-source
	${TAR} -cf ${WRKDIR:Q}/ml-dtypes-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/ml-dtypes-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/ml-dtypes-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/ml-dtypes-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
