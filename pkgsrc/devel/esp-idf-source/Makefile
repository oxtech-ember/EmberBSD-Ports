# Common ESP-IDF source and its matching Wi-Fi and PHY binary submodules.
.include "../../devel/esp-idf-source/Makefile.common"
DISTNAME= esp-idf-${ESP_IDF_VERSION}
PKGNAME= esp-idf-source-${ESP_IDF_VERSION}
CATEGORIES= devel
MASTER_SITES= # individual archives below
DISTFILES= ${DISTNAME}.tar.gz esp32-wifi-lib-${ESP_IDF_WIFI_REVISION}.tar.gz \
 esp-phy-lib-${ESP_IDF_PHY_REVISION}.tar.gz
SITES.${DISTNAME}.tar.gz= -https://github.com/espressif/esp-idf/archive/refs/tags/v${ESP_IDF_VERSION}.tar.gz
SITES.esp32-wifi-lib-${ESP_IDF_WIFI_REVISION}.tar.gz= -https://github.com/espressif/esp32-wifi-lib/archive/${ESP_IDF_WIFI_REVISION}.tar.gz
SITES.esp-phy-lib-${ESP_IDF_PHY_REVISION}.tar.gz= -https://github.com/espressif/esp-phy-lib/archive/${ESP_IDF_PHY_REVISION}.tar.gz
HOMEPAGE= https://github.com/espressif/esp-idf/
COMMENT= ESP-IDF component sources with matching Wi-Fi and PHY libraries
LICENSE= apache-2.0 AND mit AND 2-clause-bsd AND modified-bsd AND isc AND \
 cc0-1.0-universal AND gnu-gpl-v2
NO_ARCH= yes
NO_CONFIGURE= yes
NO_BUILD= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort

INSTALLATION_DIRS= share/esp-idf-source

do-install:
	${CP} -R ${WRKSRC}/components ${DESTDIR}${PREFIX}/share/esp-idf-source/
	${INSTALL_DATA} ${FILESDIR}/COPYING.BSD-4-Clause-UC ${DESTDIR}${PREFIX}/share/esp-idf-source/
	${INSTALL_DATA} ${FILESDIR}/COPYING.BSD-2-Clause-FreeBSD ${DESTDIR}${PREFIX}/share/esp-idf-source/
	${INSTALL_DATA} ${.CURDIR}/README.md ${DESTDIR}${PREFIX}/share/esp-idf-source/README.EmberBSD.md
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${WRKSRC}/README.md ${WRKSRC}/.gitmodules ${DESTDIR}${PREFIX}/share/esp-idf-source/
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/esp-idf-source/components/esp_wifi/lib
	${CP} -R ${WRKDIR}/esp32-wifi-lib-${ESP_IDF_WIFI_REVISION}/. ${DESTDIR}${PREFIX}/share/esp-idf-source/components/esp_wifi/lib/
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/esp-idf-source/components/esp_phy/lib
	${CP} -R ${WRKDIR}/esp-phy-lib-${ESP_IDF_PHY_REVISION}/. ${DESTDIR}${PREFIX}/share/esp-idf-source/components/esp_phy/lib/

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/esp-idf-source \( -type f -o -type l \) -print | ${SORT};
CHECK_INTERPRETER_SKIP+= share/esp-idf-source/*
.include "../../mk/bsd.pkg.mk"
