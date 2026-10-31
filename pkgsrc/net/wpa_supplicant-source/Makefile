# Source shared by the supplicant and consumers of its crypto primitives.
.include "../../net/wpa_supplicant/Makefile.common"
PKGNAME= wpa_supplicant-source-${WPA_SUPPLICANT_VERSION}
PKGREVISION= 1
CATEGORIES= net
HOMEPAGE= https://w1.fi/wpa_supplicant/
COMMENT= Prepared wpa_supplicant source with the common Ports patchset
LICENSE= modified-bsd
DISTINFO_FILE= ${.CURDIR}/../../net/wpa_supplicant/distinfo
PATCHDIR= ${.CURDIR}/../../net/wpa_supplicant/patches
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort
INSTALLATION_DIRS= share/wpa_supplicant-source

do-install:
	${CP} -R ${WRKSRC}/src ${DESTDIR}${PREFIX}/share/wpa_supplicant-source/
	${CP} -R ${WRKSRC}/wpa_supplicant ${DESTDIR}${PREFIX}/share/wpa_supplicant-source/
	${FIND} ${DESTDIR}${PREFIX}/share/wpa_supplicant-source -name '*.orig' -exec ${RM} {} +
	${INSTALL_DATA} ${WRKSRC}/COPYING ${DESTDIR}${PREFIX}/share/wpa_supplicant-source/
	${INSTALL_DATA} ${.CURDIR}/README.md ${DESTDIR}${PREFIX}/share/wpa_supplicant-source/README.EmberBSD.md

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/wpa_supplicant-source \( -type f -o -type l \) -print | ${SORT};
CHECK_INTERPRETER_SKIP+= share/wpa_supplicant-source/*
.include "../../mk/bsd.pkg.mk"
