# Betaflight Configurator on system Electron (Web Serial).
# Upstream application: https://github.com/betaflight/betaflight-configurator
# Firmware project named by the requester: https://github.com/betaflight/betaflight
# This recipe and the Electron shell were prepared with AI assistance.

DISTNAME=	betaflight-configurator-2026.6.2-ember1
PKGNAME=	betaflight-configurator-2026.6.2
PKGREVISION=	1
CATEGORIES=	ham
MASTER_SITES=	# empty
DISTFILES=	betaflight-configurator-2026.6.2-ember1.asar
DIST_SUBDIR=	betaflight-configurator
EXTRACT_SUFX=	.asar
EXTRACT_ONLY=

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://github.com/betaflight/betaflight-configurator
COMMENT=	Betaflight flight controller configuration (Electron + Web Serial)
LICENSE=	gnu-gpl-v3

BF_ELECTRON_MIN_PKG_VERSION=	45.3.1
BF_ELECTRON_PKGDIR=	../../devel/electron44
DEPENDS+=	electron>=${BF_ELECTRON_MIN_PKG_VERSION}<46:${BF_ELECTRON_PKGDIR}
TOOL_DEPENDS+=	node-electron-asar>=4.3.1:../../devel/node-electron-asar
BUILD_HOST_NODE=	${EMBERBSD_HOST_NODE}
BF_ASAR_MODULE=	${EMBERBSD_HOST_PREFIX}/lib/node_modules/@electron/asar/lib/asar.js

NO_CONFIGURE=	yes
INSTALLATION_DIRS+=	bin lib/betaflight-configurator share/applications \
	share/icons/hicolor/128x128/apps share/doc/betaflight-configurator

.include "../../mk/bsd.prefs.mk"

# The checksum-pinned archive supplies the unchanged upstream WebUI. The
# packaged shell is always rebuilt from this recipe, so editing files/ cannot
# silently leave the previously packed main process in the installed app.
.PHONY: betaflight-check-build-tools
pre-build pre-test: betaflight-check-build-tools
betaflight-check-build-tools:
.if !defined(EMBERBSD_HOST_PREFIX) || empty(EMBERBSD_HOST_PREFIX:M/*) || !exists(${BF_ASAR_MODULE})
	${FAIL_MSG} "Betaflight requires node-electron-asar in the selected native EMBERBSD_HOST_PREFIX"
.endif
.if !defined(EMBERBSD_HOST_NODE) || empty(EMBERBSD_HOST_NODE:M${EMBERBSD_HOST_PREFIX}/bin/*) || !exists(${EMBERBSD_HOST_NODE})
	${FAIL_MSG} "Betaflight requires EMBERBSD_HOST_NODE from the selected native prefix"
.endif

do-build:
	${BUILD_HOST_NODE:Q} ${FILESDIR:Q}/build-shell.mjs \
	    --asar-module ${BF_ASAR_MODULE:Q} \
	    --input ${DISTDIR:Q}/${DIST_SUBDIR:Q}/${DISTFILES:Q} \
	    --files ${FILESDIR:Q} --work ${WRKDIR:Q}

do-test:
	${BUILD_HOST_NODE:Q} ${PKGDIR:Q}/tests/serial.cjs
	${BUILD_HOST_NODE:Q} ${PKGDIR:Q}/tests/app-paths.cjs

do-install:
	${INSTALL_DATA} ${WRKDIR}/app.asar \
	    ${DESTDIR}${PREFIX}/lib/betaflight-configurator/app.asar
	${SED} 's|@PREFIX@|${PREFIX}|g' ${FILESDIR}/betaflight-configurator.sh \
	    > ${WRKDIR}/betaflight-configurator
	${INSTALL_SCRIPT} ${WRKDIR}/betaflight-configurator \
	    ${DESTDIR}${PREFIX}/bin/betaflight-configurator
	${SED} 's|@PREFIX@|${PREFIX}|g' ${FILESDIR}/betaflight-configurator.desktop \
	    > ${WRKDIR}/org.betaflight.configurator.desktop
	${INSTALL_DATA} ${WRKDIR}/org.betaflight.configurator.desktop \
	    ${DESTDIR}${PREFIX}/share/applications/org.betaflight.configurator.desktop
	${INSTALL_DATA} ${FILESDIR}/betaflight-configurator.png \
	    ${DESTDIR}${PREFIX}/share/icons/hicolor/128x128/apps/org.betaflight.configurator.png
	${INSTALL_DATA} ${PKGDIR}/DESCR \
	    ${DESTDIR}${PREFIX}/share/doc/betaflight-configurator/DESCR

.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../mk/bsd.pkg.mk"
