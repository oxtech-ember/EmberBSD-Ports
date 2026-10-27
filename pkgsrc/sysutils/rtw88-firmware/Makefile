DISTNAME=	rtw88-firmware-48
CATEGORIES=	sysutils

COMMENT=	Firmware image for the RTL8723D WLAN device
LICENSE=	rtlwifi-firmware-license
LICENSE_FILE=	${WRKSRC}/LICENSES/LICENCE.rtlwifi_firmware.txt

DIST_SUBDIR=	rtw88-firmware/0a62bdcabeae4666e87f3fba3b7fe116d7414034
DISTFILES=	rtw8723d_fw.bin WHENCE LICENCE.rtlwifi_firmware.txt
SITES.rtw8723d_fw.bin=	-https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/rtw88/rtw8723d_fw.bin?id=0a62bdcabeae4666e87f3fba3b7fe116d7414034
SITES.WHENCE=	-https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/WHENCE?id=0a62bdcabeae4666e87f3fba3b7fe116d7414034
SITES.LICENCE.rtlwifi_firmware.txt=	-https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/LICENSES/LICENCE.rtlwifi_firmware.txt?id=0a62bdcabeae4666e87f3fba3b7fe116d7414034

WRKSRC=		${WRKDIR}
EXTRACT_ONLY=
NO_CONFIGURE=	yes
NO_BUILD=	yes

INSTALLATION_DIRS=	libdata/firmware/rtw88 \
			share/doc/rtw88-firmware \
			share/licenses/rtw88-firmware

do-extract:
	${MKDIR} ${WRKSRC}/rtw88 ${WRKSRC}/LICENSES
	${CP} ${DISTDIR}/${DIST_SUBDIR}/rtw8723d_fw.bin ${WRKSRC}/rtw88/
	${CP} ${DISTDIR}/${DIST_SUBDIR}/WHENCE ${WRKSRC}/
	${CP} ${DISTDIR}/${DIST_SUBDIR}/LICENCE.rtlwifi_firmware.txt \
	    ${WRKSRC}/LICENSES/

do-install:
	${INSTALL_DATA} ${WRKSRC}/rtw88/rtw8723d_fw.bin \
	    ${DESTDIR}${PREFIX}/libdata/firmware/rtw88/
	${INSTALL_DATA} ${WRKSRC}/WHENCE \
	    ${DESTDIR}${PREFIX}/share/doc/rtw88-firmware/
	${INSTALL_DATA} ${WRKSRC}/LICENSES/LICENCE.rtlwifi_firmware.txt \
	    ${DESTDIR}${PREFIX}/share/licenses/rtw88-firmware/

.include "../../mk/bsd.pkg.mk"
