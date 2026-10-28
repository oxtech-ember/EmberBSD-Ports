# EmberBSD: Qt 6 Wi-Fi tray manager for wpa_supplicant.
DISTNAME= EmberBSD-Examples
PKGNAME= ember-wifi-0.1.0
PKGREVISION= 3
CATEGORIES= net
MASTER_SITES= ${MASTER_SITE_GITHUB:=oxtech-ember/}
GITHUB_PROJECT= EmberBSD-Examples
GITHUB_TAG= d233a5fa2ce913cd496a22c4ad522ad9a9e204c9
WRKSRC= ${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}/desktop/ember-wifi

HOMEPAGE= https://github.com/oxtech-ember/EmberBSD-Examples/tree/${GITHUB_TAG}/desktop/ember-wifi
COMMENT= Qt 6 tray Wi-Fi manager for wpa_supplicant
LICENSE= 2-clause-bsd

USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
TEST_TARGET= test
CMAKE_CONFIGURE_ARGS+= -DCMAKE_INSTALL_RPATH:STRING=${PREFIX}/qt6/lib:${PREFIX}/lib:/usr/X11R7/lib

BUILDLINK_API_DEPENDS.kf6-kdbusaddons+= kf6-kdbusaddons>=6.31.0
BUILDLINK_API_DEPENDS.qt6-qtbase+= qt6-qtbase>=6.12.0

.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
CMAKE_CONFIGURE_ARGS+= -DCMAKE_SKIP_RPATH:BOOL=FALSE
