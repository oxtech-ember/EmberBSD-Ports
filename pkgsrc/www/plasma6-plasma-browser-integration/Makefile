# $NetBSD$

DISTNAME=	plasma-browser-integration-${PLASMAVER}
CATEGORIES=	www

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Components to integrate browsers into the Plasma desktop
LICENSE=	gnu-gpl-v3

.include "../../meta-pkgs/kde/plasma6.mk"

# Do not install a manifest that downloads a browser extension.
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_CHROME_MANIFEST=OFF

USE_TOOLS+=	msgmerge pkg-config

.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-krunner/buildlink3.mk"
.include "../../devel/kf6-kservice/buildlink3.mk"
.include "../../devel/kf6-purpose/buildlink3.mk"
.include "../../misc/kf6-kstatusnotifieritem/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../sysutils/kf6-kfilemetadata/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../sysutils/plasma6-libksysguard/buildlink3.mk"
.include "../../x11/plasma6-plasma-workspace/buildlink3.mk"
.include "../../x11/kf6-kjobwidgets/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
