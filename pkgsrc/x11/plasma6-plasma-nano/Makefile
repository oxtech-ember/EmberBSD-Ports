# $NetBSD$

DISTNAME=	plasma-nano-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Minimal Plasma shell for constrained embedded devices
LICENSE=	gnu-lgpl-v2.1 OR gnu-gpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

USE_TOOLS+=	msgmerge

.include "../../devel/kf6-kitemmodels/buildlink3.mk"
.include "../../devel/kf6-kservice/buildlink3.mk"
.include "../../graphics/qt6-qtsvg/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../devel/plasma6-kwayland/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
