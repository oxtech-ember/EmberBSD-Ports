# $NetBSD$

DISTNAME=	plasma-mobile-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://plasma-mobile.org/
COMMENT=	Plasma shell additions for mobile form factors
LICENSE=	gnu-gpl-v3 AND gnu-lgpl-v2.1-or-later AND mit

.include "../../meta-pkgs/kde/plasma6.mk"

USE_CXX_FEATURES+=	c++20
USE_TOOLS+=		msgmerge pkg-config

# The recording quick setting is dropped with KPipeWire; see the patches.
SUBST_CLASSES+=		qmlpipewire
SUBST_STAGE.qmlpipewire=	post-patch
SUBST_FILES.qmlpipewire=	shell/contents/configuration/AboutPlugins.qml
SUBST_NOOP_OK.qmlpipewire=	yes

.include "../../security/kf6-kauth/buildlink3.mk"
.include "../../devel/kf6-kitemmodels/buildlink3.mk"
.include "../../net/modemmanager-qt/buildlink3.mk"
.include "../../net/networkmanager-qt/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/qcoro/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../x11/kirigami-addons/buildlink3.mk"
.include "../../graphics/libepoxy/buildlink3.mk"
.include "../../x11/kf6-kconfigwidgets/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../graphics/kf6-ksvg/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/kf6-kxmlgui/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../devel/plasma6-kwayland/buildlink3.mk"
.include "../../x11/plasma6-kwin/buildlink3.mk"
.include "../../x11/plasma6-layer-shell-qt/buildlink3.mk"
.include "../../x11/plasma6-libkscreen/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities/buildlink3.mk"
.include "../../x11/plasma6-plasma-workspace/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/xcb-util/buildlink3.mk"
.include "../../x11/xcb-util-cursor/buildlink3.mk"
.include "../../x11/xcb-util-keysyms/buildlink3.mk"
.include "../../x11/xcb-util-wm/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
