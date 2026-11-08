# $NetBSD$

DISTNAME=	bluez-qt-${KF6VER}
CATEGORIES=	net

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Qt D-Bus binding for the BlueZ interface
LICENSE=	gnu-lgpl-v2.1 AND gnu-lgpl-v3

.include "../../meta-pkgs/kde/kf6.mk"

# This is the D-Bus client library. It does not talk to a local BlueZ
# daemon and does not open /dev/rfkill. The QML module is built and is
# not loaded.

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF

.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
