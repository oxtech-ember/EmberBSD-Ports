# Origin: EmberBSD contributors (AI-assisted); shared OpenXLA/TSL source owner.
# Upstream has no stable release tags; use one current, explicitly dated snapshot.
OPENXLA_REVISION= 13cab0c9fd4224a9f397f30b575f783b2c3da980
OPENXLA_DATE= 20261105
DISTNAME= xla-${OPENXLA_REVISION}
PKGNAME= openxla-source-0.0.${OPENXLA_DATE}
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=openxla/}
GITHUB_PROJECT= xla
GITHUB_TAG= ${OPENXLA_REVISION}
DISTFILES= ${DISTNAME}${EXTRACT_SUFX}
SITES.${DISTNAME}.tar.gz= -https://github.com/openxla/xla/archive/${OPENXLA_REVISION}.tar.gz
HOMEPAGE= https://github.com/openxla/xla
COMMENT= Shared OpenXLA and TSL sources
LICENSE= apache-2.0
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar
CHECK_INTERPRETER_SKIP+= share/openxla-source/*

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/openxla-source
	${TAR} -cf ${WRKDIR:Q}/openxla-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/openxla-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/openxla-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/openxla-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
