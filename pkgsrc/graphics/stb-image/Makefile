# Origin: EmberBSD (AI-assisted); common upstream stb_image provider.
DISTNAME= stb-image-2.30.20261023
CATEGORIES= graphics
STB_REVISION= 003501f6d7a8668ce8b6d875e34dd97ad0d5d5b5
MASTER_SITES= -https://github.com/nothings/stb/archive/${STB_REVISION}.tar.gz
WRKSRC= ${WRKDIR}/stb-${STB_REVISION}
HOMEPAGE= https://github.com/nothings/stb
COMMENT= Single-header image decoding library
LICENSE= mit OR public-domain
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # header-only library

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/include/stb
	${INSTALL_DATA} ${WRKSRC:Q}/stb_image.h ${DESTDIR:Q}${PREFIX:Q}/include/stb/
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/licenses/stb-image
	${INSTALL_DATA} ${WRKSRC:Q}/LICENSE ${DESTDIR:Q}${PREFIX:Q}/share/licenses/stb-image/LICENSE

.include "../../mk/bsd.pkg.mk"
