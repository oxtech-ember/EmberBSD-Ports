# $NetBSD$

DISTNAME=	plasma-integration-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Integration of Qt application with KDE workspaces
LICENSE=	gnu-lgpl-v2 AND gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/plasma6.mk"

# The platform plugin is built. It is not selected as the session Qt
# platform theme. Noto Sans is already installed by noto-fonts. The
# upstream font packages are not linked, and cmake is told not to
# require them.

DEPENDS+=	plasma6-xdg-desktop-portal-kde>=6.8.2:../../misc/plasma6-xdg-desktop-portal-kde
DEPENDS+=	kf6-qqc2-desktop-style>=6.31.0:../../x11/kf6-qqc2-desktop-style
DEPENDS+=	qt6-qtdeclarative>=6.12.0:../../lang/qt6-qtdeclarative

USE_TOOLS+=	msgmerge pkg-config

CMAKE_CONFIGURE_ARGS+=	-DBUILD_QT5=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_FontNotoSans=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_FontNotoColorEmoji=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_FontHack=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_XDGDesktopPortalKDE=ON

.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/plasma6-kwayland/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../misc/kf6-kstatusnotifieritem/buildlink3.mk"
.include "../../x11/kf6-kconfigwidgets/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/kf6-kxmlgui/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
