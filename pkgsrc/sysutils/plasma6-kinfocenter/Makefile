# $NetBSD: Makefile,v 1.10 2026/09/06 10:23:30 markd Exp $

DISTNAME=	kinfocenter-${PLASMAVER}
CATEGORIES=	sysutils

HOMEPAGE=	https://www.kde.org/workspaces/plasmadesktop/
COMMENT=	Utility that provides information about a computer system
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2.1 AND gnu-fdl-v1.2

.include "../../meta-pkgs/kde/plasma6.mk"

# The host already has kf6-kdoctools-generators. The full package conflicts with it.
# glxinfo, vulkaninfo, lscpu and xdpyinfo are not available in this package set.
# The OpenGL, Vulkan and X11 information pages cannot run those commands.
DEPENDS+=	plasma6-systemsettings>=${PLASMAVER}:../../sysutils/plasma6-systemsettings
DEPENDS+=	qt6-qtdeclarative>=6.12.0:../../lang/qt6-qtdeclarative

USE_TOOLS+=	msgmerge pkg-config

.include "../../sysutils/desktop-file-utils/desktopdb.mk"
BUILDLINK_API_DEPENDS.pciutils+=	pciutils>=3.8
.include "../../sysutils/pciutils/buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/plasma6-kwayland/buildlink3.mk"
.include "../../devel/libusb1/buildlink3.mk"
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../graphics/vulkan-headers/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/libdrm/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
