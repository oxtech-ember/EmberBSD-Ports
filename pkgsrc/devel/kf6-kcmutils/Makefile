# $NetBSD: Makefile,v 1.26 2026/09/06 10:05:11 markd Exp $

PKGREVISION=	2

.include "Makefile.common"

COMMENT=	Utilities for interacting with KCModules

USE_TOOLS+=	msgmerge

.include "../../meta-pkgs/kde/kf6.mk"

# patch-tools_CMakeLists.txt imports the native generator in cross builds.
.include "cross-tools.mk"

.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/kf6-kconfigwidgets/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kitemviews/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../x11/kf6-kxmlgui/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
