# $NetBSD$

DISTNAME=	plasma-firewall-${PLASMAVER}
CATEGORIES=	sysutils

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Firewall settings module for Plasma
LICENSE=	modified-bsd AND gnu-gpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

# Upstream compiles the firewalld and ufw backends only when the target
# system is Linux. This NetBSD build keeps the module and the netstat
# view. No firewall rule is written and no daemon is started.

USE_TOOLS+=	msgmerge pkg-config

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF

.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../security/kf6-kauth/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
