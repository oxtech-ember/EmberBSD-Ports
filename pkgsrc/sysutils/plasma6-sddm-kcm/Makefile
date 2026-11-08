# $NetBSD$

DISTNAME=	sddm-kcm-${PLASMAVER}
CATEGORIES=	sysutils

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	SDDM configuration module for System Settings
LICENSE=	gnu-gpl-v2 AND gnu-gpl-v3

.include "../../meta-pkgs/kde/plasma6.mk"

# The module and its privileged helper are built only. Nothing here
# selects SDDM or writes a login configuration.

USE_TOOLS+=	msgmerge pkg-config

.include "../../archivers/kf6-karchive/buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-kservice/buildlink3.mk"
.include "../../net/kf6-knewstuff/buildlink3.mk"
.include "../../security/kf6-kauth/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
