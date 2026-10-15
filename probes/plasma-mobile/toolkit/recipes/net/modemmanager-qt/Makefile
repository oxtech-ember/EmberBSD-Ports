# $NetBSD$

DISTNAME=	modemmanager-qt-6.31.0
CATEGORIES=	net
EXTRACT_SUFX=	.tar.xz

HOMEPAGE=	https://api.kde.org/frameworks/networkmanager-qt/html/
COMMENT=	Qt bindings for the ModemManager DBus interface
LICENSE=	gnu-lgpl-v2.1

.include "../../mk/bsd.prefs.mk"

USE_CMAKE=	yes
USE_LANGUAGES=	c c++
GCC_REQD+=	16.2
USE_TOOLS+=	pkg-config
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+= -DKF_IGNORE_PLATFORM_CHECK=ON

.include "../../devel/modemmanager-headers/buildlink3.mk"
.include "../../net/networkmanager-headers/buildlink3.mk"

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
