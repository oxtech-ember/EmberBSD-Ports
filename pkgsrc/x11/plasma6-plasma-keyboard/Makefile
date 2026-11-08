# $NetBSD$

DISTNAME=	plasma-keyboard-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Virtual keyboard for Plasma
LICENSE=	gnu-lgpl-v2.1 AND gnu-gpl-v3

.include "../../meta-pkgs/kde/plasma6.mk"

# The keyboard and its settings module are built only. The session input
# method is not changed.

USE_TOOLS+=	msgmerge pkg-config

.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../inputmethod/qt6-qtvirtualkeyboard/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/plasma6-plasma-workspace/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
