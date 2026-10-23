# $NetBSD: Makefile,v 1.16 2026/09/06 10:05:20 markd Exp $

DISTNAME=	kconfigwidgets-${KF6VER}
PKGREVISION=	1
CATEGORIES=	x11

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Widgets for KConfig
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../devel/kf6-kdoctools/tools.mk"

USE_TOOLS+= msgmerge

# Upstream 6.31 no longer installs preparetips6; no Perl runtime is needed.

.include "../../lang/python/tool.mk"
.include "../../devel/kf6-kcolorscheme/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
# Designer headers are build inputs; the plugin links Qtbase and Frameworks.
BUILDLINK_DEPMETHOD.qt6-qttools= build
.include "../../devel/qt6-qttools/buildlink3.mk"
.include "../../devel/qt6-qttools/linguist.mk"
.include "../../security/kf6-kauth/buildlink3.mk"
.include "../../textproc/kf6-kcodecs/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
