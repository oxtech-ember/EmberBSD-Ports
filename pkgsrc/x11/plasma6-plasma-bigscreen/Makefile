# $NetBSD$

DISTNAME=	plasma-bigscreen-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://plasma-bigscreen.org/
COMMENT=	Plasma shell for large displays
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/plasma6.mk"

# The shell is built and not selected. The webapp viewer needs Qt WebEngine,
# which is not in this sysroot. The controller process calls the Linux
# EVIOCGUNIQ ioctl and is not built. Neither is started.

USE_TOOLS+=	msgmerge pkg-config

DEPENDS+=	qt6-qtdeclarative>=6.12.0:../../lang/qt6-qtdeclarative
DEPENDS+=	kf6-kpackage>=6.31.0:../../devel/kf6-kpackage

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_WEBAPP_VIEWER:BOOL=OFF

.include "../../devel/SDL3/buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcolorscheme/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/qcoro/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../graphics/kf6-ksvg/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../multimedia/qt6-qtmultimedia/buildlink3.mk"
.include "../../net/kdeconnect-kde/buildlink3.mk"
.include "../../net/kf6-bluez-qt/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../x11/kf6-kglobalaccel/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/plasma6-libkscreen/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities-stats/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities/buildlink3.mk"
.include "../../x11/plasma6-plasma-workspace/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
