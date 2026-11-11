# 100 is the firmware API number in the upstream file name; WHENCE lists
# the image itself as version 97.3f3ef548.0.
DISTNAME=	iwx-firmware-100
CATEGORIES=	sysutils

COMMENT=	Firmware images for the Intel BE200 iwx WLAN device
LICENSE=	iwlwifi-firmware-license
LICENSE_FILE=	${WRKSRC}/LICENSES/LICENCE.iwlwifi_firmware

DIST_SUBDIR=	iwx-firmware/69e51bb26f3fa3e118dd770f1962a93bed690dc1
DISTFILES=	iwlwifi-gl-c0-fm-c0-100.ucode iwlwifi-gl-c0-fm-c0.pnvm WHENCE LICENCE.iwlwifi_firmware
SITES.iwlwifi-gl-c0-fm-c0-100.ucode=	-https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/intel/iwlwifi/iwlwifi-gl-c0-fm-c0-100.ucode?id=69e51bb26f3fa3e118dd770f1962a93bed690dc1
SITES.iwlwifi-gl-c0-fm-c0.pnvm=	-https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/intel/iwlwifi/iwlwifi-gl-c0-fm-c0.pnvm?id=69e51bb26f3fa3e118dd770f1962a93bed690dc1
SITES.WHENCE=	-https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/WHENCE?id=69e51bb26f3fa3e118dd770f1962a93bed690dc1
SITES.LICENCE.iwlwifi_firmware=	-https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/LICENSES/LICENCE.iwlwifi_firmware?id=69e51bb26f3fa3e118dd770f1962a93bed690dc1

WRKSRC=		${WRKDIR}
EXTRACT_ONLY=
NO_CONFIGURE=	yes
NO_BUILD=	yes

INSTALLATION_DIRS=	libdata/firmware/if_iwx \
			share/doc/iwx-firmware \
			share/licenses/iwx-firmware

do-extract:
	${MKDIR} ${WRKSRC}/intel/iwlwifi ${WRKSRC}/LICENSES
	${CP} ${DISTDIR}/${DIST_SUBDIR}/iwlwifi-gl-c0-fm-c0-100.ucode \
	    ${WRKSRC}/intel/iwlwifi/
	${CP} ${DISTDIR}/${DIST_SUBDIR}/iwlwifi-gl-c0-fm-c0.pnvm \
	    ${WRKSRC}/intel/iwlwifi/
	${CP} ${DISTDIR}/${DIST_SUBDIR}/WHENCE ${WRKSRC}/
	${CP} ${DISTDIR}/${DIST_SUBDIR}/LICENCE.iwlwifi_firmware \
	    ${WRKSRC}/LICENSES/

# iwx(4) asks firmload(9) for these names in the if_iwx directory.
do-install:
	${INSTALL_DATA} ${WRKSRC}/intel/iwlwifi/iwlwifi-gl-c0-fm-c0-100.ucode \
	    ${DESTDIR}${PREFIX}/libdata/firmware/if_iwx/iwx-gl-c0-fm-c0-100
	${INSTALL_DATA} ${WRKSRC}/intel/iwlwifi/iwlwifi-gl-c0-fm-c0.pnvm \
	    ${DESTDIR}${PREFIX}/libdata/firmware/if_iwx/iwx-gl-c0-fm-c0.pnvm
	${INSTALL_DATA} ${WRKSRC}/WHENCE \
	    ${DESTDIR}${PREFIX}/share/doc/iwx-firmware/
	${INSTALL_DATA} ${WRKSRC}/LICENSES/LICENCE.iwlwifi_firmware \
	    ${DESTDIR}${PREFIX}/share/licenses/iwx-firmware/

.include "../../mk/bsd.pkg.mk"
