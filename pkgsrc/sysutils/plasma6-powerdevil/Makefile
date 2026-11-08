# $NetBSD: Makefile,v 1.7 2026/09/09 11:51:45 markd Exp $

DISTNAME=	powerdevil-${PLASMAVER}
PKGREVISION=	1
CATEGORIES=	sysutils

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Manages the power consumption settings of a Plasma Shell
LICENSE=	gnu-lgpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

# The host already has kf6-kdoctools-generators. The full package conflicts with it.
USE_TOOLS+=	msgmerge pkg-config

USE_CXX_FEATURES+=	c++23

SUBST_CLASSES+=		xdg
SUBST_STAGE.xdg=	pre-configure
SUBST_MESSAGE.xdg=	Install via examples dir.
SUBST_FILES.xdg=	daemon/CMakeLists.txt
SUBST_SED.xdg=		-e 's:{KDE_INSTALL_AUTOSTARTDIR}:{KDE_INSTALL_AUTOSTARTEXDIR}:'

# The upstream idle default suspends when ConsoleKit reports suspend.
# Do not copy that desktop file into the active autostart directory.
post-extract:
	${CP} ${FILESDIR}/backlighthelper_netbsd.cpp ${WRKSRC}/daemon/controllers/backlighthelper_netbsd.cpp
	${CP} ${FILESDIR}/backlighthelper_netbsd.h ${WRKSRC}/daemon/controllers/backlighthelper_netbsd.h
	${CP} ${FILESDIR}/chargethresholdhelper_netbsd.cpp ${WRKSRC}/daemon/chargethresholdhelper_netbsd.cpp

.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kidletime/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-kitemmodels/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/kf6-krunner/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/qcoro/buildlink3.mk"
.include "../../security/kf6-kauth/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../sysutils/kf6-solid/buildlink3.mk"
.include "../../x11/kf6-kglobalaccel/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/kf6-kxmlgui/buildlink3.mk"
.include "../../x11/plasma6-libkscreen/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities/buildlink3.mk"
.include "../../x11/plasma6-plasma-workspace/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../devel/kf6-kpackage/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
