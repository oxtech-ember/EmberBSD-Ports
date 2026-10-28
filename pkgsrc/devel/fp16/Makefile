# Origin: EmberBSD (AI-assisted); upstream FP16 header-only provider.
DISTNAME= fp16-0.0.0pre20260620
CATEGORIES= devel
FP16_REVISION= 782eea126dc5c755827be751a099eb01826175cf
MASTER_SITES= -https://github.com/Maratyszcza/FP16/archive/${FP16_REVISION}.tar.gz
WRKSRC= ${WRKDIR}/FP16-${FP16_REVISION}
HOMEPAGE= https://github.com/Maratyszcza/FP16
COMMENT= Portable IEEE half precision floating-point conversion headers
LICENSE= mit
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # header-only library

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/include/fp16
	${INSTALL_DATA} ${WRKSRC:Q}/include/fp16.h ${DESTDIR:Q}${PREFIX:Q}/include/
	${INSTALL_DATA} ${WRKSRC:Q}/include/fp16/*.h ${DESTDIR:Q}${PREFIX:Q}/include/fp16/
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/licenses/fp16
	${INSTALL_DATA} ${WRKSRC:Q}/LICENSE ${DESTDIR:Q}${PREFIX:Q}/share/licenses/fp16/LICENSE

.include "../../mk/bsd.pkg.mk"
