# Origin: EmberBSD contributors (AI-assisted); upstream shared source owner.
DISTNAME= fxdiv-63058eff77e11aa15bf531df5dd34395ec3017c8
PKGNAME= fxdiv-source-0.0.20201209
CATEGORIES= devel
MASTER_SITES= -https://github.com/Maratyszcza/FXdiv/archive/63058eff77e11aa15bf531df5dd34395ec3017c8.tar.gz
WRKSRC= ${WRKDIR}/FXdiv-63058eff77e11aa15bf531df5dd34395ec3017c8
HOMEPAGE= https://github.com/Maratyszcza/FXdiv
COMMENT= Shared fxdiv upstream source for SDK consumers
LICENSE= mit
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar
CHECK_INTERPRETER_SKIP+= share/fxdiv-source/*

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/fxdiv-source
	${TAR} -cf ${WRKDIR:Q}/fxdiv-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/fxdiv-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/fxdiv-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/fxdiv-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
