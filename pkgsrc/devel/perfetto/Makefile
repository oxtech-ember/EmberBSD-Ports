# Origin: EmberBSD (AI-assisted); shared Perfetto source owner.
DISTNAME= perfetto-59.1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=google/}
GITHUB_PROJECT= perfetto
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://perfetto.dev/
COMMENT= Shared Perfetto tracing source
LICENSE= apache-2.0
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar

# The pinned upstream archive has no .orig files; pkgsrc creates patch backups.
do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/perfetto-source
	${TAR} -cf ${WRKDIR:Q}/perfetto-source.tar --exclude '*.orig' -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/perfetto-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/perfetto-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/perfetto-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
