# $NetBSD$

DISTNAME=	polkit-kde-agent-1-${PLASMAVER}
PKGNAME=	plasma6-polkit-kde-agent-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Polkit authentication dialog for KDE
LICENSE=	gnu-gpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

# The dialog is built. The autostart file is installed as an example.
# It is not copied into the session autostart directory and the agent
# is not started. Documentation tools are not required to compile it.

USE_TOOLS+=	msgmerge pkg-config

SUBST_CLASSES+=		xdg
SUBST_STAGE.xdg=	pre-configure
SUBST_MESSAGE.xdg=	Install via examples dir.
SUBST_FILES.xdg=	CMakeLists.txt
SUBST_SED.xdg=		-e 's:{KDE_INSTALL_AUTOSTARTDIR}:{KDE_INSTALL_AUTOSTARTEXDIR}:'

DEPENDS+=	qt6-qtdeclarative>=6.12.0:../../lang/qt6-qtdeclarative

.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../security/polkit-qt6/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
