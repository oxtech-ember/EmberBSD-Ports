# $NetBSD$
DISTNAME= libyuv-d2a64963531e80a329109705dc0ed2b575eba909
PKGNAME= libyuv-0.0.1978
CATEGORIES= multimedia
MASTER_SITES= -https://gitlab.com/chromiumsrc/libyuv/-/archive/d2a64963531e80a329109705dc0ed2b575eba909/libyuv-d2a64963531e80a329109705dc0ed2b575eba909.tar.gz
HOMEPAGE= https://chromium.googlesource.com/libyuv/libyuv/
COMMENT= Image conversion and scaling library
LICENSE= modified-bsd
USE_LANGUAGES= c c++
CMAKE_CONFIGURE_ARGS+= -DUNIT_TEST=OFF
INSTALLATION_DIRS+= include/libyuv lib
do-install:
	${INSTALL_DATA} ${WRKSRC}/include/libyuv.h ${DESTDIR}${PREFIX}/include/
	${INSTALL_DATA} ${WRKSRC}/include/libyuv/*.h ${DESTDIR}${PREFIX}/include/libyuv/
	${INSTALL_LIB} ${WRKSRC}/${CMAKE_BUILD_DIR}/libyuv.${SHLIB_EXT} ${DESTDIR}${PREFIX}/lib/
.include "../../mk/jpeg.buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
