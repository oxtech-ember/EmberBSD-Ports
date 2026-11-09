# The version is the commit date of LINUX_FIRMWARE_COMMIT (2026-10-26).
# WHENCE lists rtl_bt/rtl8821c_* under LICENCE.rtlwifi_firmware.txt.
DISTNAME=	rtl-bt-firmware-20261026
CATEGORIES=	sysutils

COMMENT=	Patch firmware for Realtek Bluetooth controllers (rtlbtfw)
LICENSE=	rtlwifi-firmware-license
LICENSE_FILE=	${WRKSRC}/LICENSES/LICENCE.rtlwifi_firmware.txt

LINUX_FIRMWARE_COMMIT=	0a62bdcabeae4666e87f3fba3b7fe116d7414034
LINUX_FIRMWARE_PLAIN=	https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain
DIST_SUBDIR=	rtl-bt-firmware/${LINUX_FIRMWARE_COMMIT}
DISTFILES=	rtl8821c_fw.bin rtl8821c_config.bin WHENCE LICENCE.rtlwifi_firmware.txt
SITES.rtl8821c_fw.bin=	-${LINUX_FIRMWARE_PLAIN}/rtl_bt/rtl8821c_fw.bin?id=${LINUX_FIRMWARE_COMMIT}
SITES.rtl8821c_config.bin=	-${LINUX_FIRMWARE_PLAIN}/rtl_bt/rtl8821c_config.bin?id=${LINUX_FIRMWARE_COMMIT}
SITES.WHENCE=	-${LINUX_FIRMWARE_PLAIN}/WHENCE?id=${LINUX_FIRMWARE_COMMIT}
SITES.LICENCE.rtlwifi_firmware.txt=	-${LINUX_FIRMWARE_PLAIN}/LICENSES/LICENCE.rtlwifi_firmware.txt?id=${LINUX_FIRMWARE_COMMIT}

WRKSRC=		${WRKDIR}
EXTRACT_ONLY=
NO_CONFIGURE=	yes
NO_BUILD=	yes

INSTALLATION_DIRS=	libdata/firmware/rtl_bt \
			share/doc/rtl-bt-firmware \
			share/licenses/rtl-bt-firmware

do-extract:
	${MKDIR} ${WRKSRC}/rtl_bt ${WRKSRC}/LICENSES
	${CP} ${DISTDIR}/${DIST_SUBDIR}/rtl8821c_fw.bin ${WRKSRC}/rtl_bt/
	${CP} ${DISTDIR}/${DIST_SUBDIR}/rtl8821c_config.bin ${WRKSRC}/rtl_bt/
	${CP} ${DISTDIR}/${DIST_SUBDIR}/WHENCE ${WRKSRC}/
	${CP} ${DISTDIR}/${DIST_SUBDIR}/LICENCE.rtlwifi_firmware.txt \
	    ${WRKSRC}/LICENSES/

do-install:
	${INSTALL_DATA} ${WRKSRC}/rtl_bt/rtl8821c_fw.bin \
	    ${DESTDIR}${PREFIX}/libdata/firmware/rtl_bt/
	${INSTALL_DATA} ${WRKSRC}/rtl_bt/rtl8821c_config.bin \
	    ${DESTDIR}${PREFIX}/libdata/firmware/rtl_bt/
	${INSTALL_DATA} ${WRKSRC}/WHENCE \
	    ${DESTDIR}${PREFIX}/share/doc/rtl-bt-firmware/
	${INSTALL_DATA} ${WRKSRC}/LICENSES/LICENCE.rtlwifi_firmware.txt \
	    ${DESTDIR}${PREFIX}/share/licenses/rtl-bt-firmware/

.include "../../mk/bsd.pkg.mk"
