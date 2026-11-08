# $NetBSD$

DISTNAME=	print-manager-${PLASMAVER}
CATEGORIES=	print

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Printer management for Plasma
LICENSE=	gnu-gpl-v2 AND gnu-gpl-v3 AND gnu-lgpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

# PackageKit would offer to install system-config-printer. Leave it off.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_WITH_CUPS3=OFF

USE_TOOLS+=	msgmerge pkg-config

.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kcolorscheme/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../print/libcups/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../x11/kf6-kconfigwidgets/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../x11/kirigami-addons/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
