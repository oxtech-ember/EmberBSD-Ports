# $NetBSD$
# Origin: EmberBSD (AI-assisted); common C software renderer.
DISTNAME= lvgl-v9.6.0-lite
PKGNAME= lvgl-9.6.0
CATEGORIES= graphics
MASTER_SITES= https://github.com/lvgl/lvgl/releases/download/v9.6.0/
EXTRACT_SUFX= .zip
EXTRACT_USING= bsdtar
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://lvgl.io/
COMMENT= Portable C graphics and user interface library
LICENSE= mit AND ofl-v1.1
USE_LANGUAGES= c
CMAKE_CONFIGURE_ARGS+= -DLV_BUILD_C_ONLY=ON -DLV_BUILD_USE_LIBM=OFF
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=OFF
CMAKE_CONFIGURE_ARGS+= -DLV_BUILD_CONF_PATH=${FILESDIR}/lv_conf.h
CMAKE_CONFIGURE_ARGS+= -DLV_FETCH_DEPENDENCIES=OFF
CMAKE_CONFIGURE_ARGS+= -DLV_USE_FIND_PACKAGE=OFF -DLV_USE_PKG_CONFIG=OFF
CMAKE_CONFIGURE_ARGS+= -DCONFIG_LV_BUILD_EXAMPLES=OFF -DCONFIG_LV_BUILD_DEMOS=OFF
CMAKE_CONFIGURE_ARGS+= -DCONFIG_LV_USE_THORVG=OFF -DCONFIG_LV_USE_THORVG_INTERNAL=OFF

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/lvgl
	${INSTALL_DATA} ${WRKSRC}/LICENCE.txt ${DESTDIR}${PREFIX}/share/licenses/lvgl/LICENCE.txt
	${INSTALL_DATA} ${WRKSRC}/COPYRIGHTS.md ${DESTDIR}${PREFIX}/share/licenses/lvgl/COPYRIGHTS.md
	${INSTALL_DATA} ${FILESDIR}/OFL-Montserrat.txt ${DESTDIR}${PREFIX}/share/licenses/lvgl/OFL-Montserrat.txt
	${INSTALL_DATA} ${FILESDIR}/Font-Awesome-LICENSE.txt ${DESTDIR}${PREFIX}/share/licenses/lvgl/Font-Awesome-LICENSE.txt

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
