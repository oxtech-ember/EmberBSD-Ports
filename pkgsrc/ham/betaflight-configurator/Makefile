# Betaflight Configurator on system Electron (Web Serial).
# Upstream application: https://github.com/betaflight/betaflight-configurator
# Firmware project named by the requester: https://github.com/betaflight/betaflight
# This recipe and the Electron shell were prepared with AI assistance.

DISTNAME=	betaflight-configurator-2026.6.2-ember1
PKGNAME=	betaflight-configurator-2026.6.2
PKGREVISION=	0
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

BF_ELECTRON_MIN_PKG_VERSION=	45.2.1nb2
BF_ELECTRON_PKGDIR=	../../devel/electron44
DEPENDS+=	electron>=${BF_ELECTRON_MIN_PKG_VERSION}<45.2.2:${BF_ELECTRON_PKGDIR}

NO_CONFIGURE=	yes
NO_BUILD=	yes
INSTALLATION_DIRS+=	bin lib/betaflight-configurator share/applications \
	share/icons/hicolor/128x128/apps share/doc/betaflight-configurator

.include "../../mk/bsd.prefs.mk"

do-install:
	${INSTALL_DATA} ${DISTDIR}/${DIST_SUBDIR}/${DISTFILES} \
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
