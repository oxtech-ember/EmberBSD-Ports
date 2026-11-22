# $NetBSD$

DISTNAME=	bluez-qt-${KF6VER}
CATEGORIES=	net

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Qt D-Bus binding for the BlueZ interface
LICENSE=	gnu-lgpl-v2.1 AND gnu-lgpl-v3

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} != "Linux"
PKGREVISION=	1
.endif
.if ${OPSYS} == "NetBSD" || ${OPSYS} == "Darwin" || ${OPSYS} == "Linux"
KF6_IGNORE_PLATFORM_CHECK=	OFF
.endif

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
