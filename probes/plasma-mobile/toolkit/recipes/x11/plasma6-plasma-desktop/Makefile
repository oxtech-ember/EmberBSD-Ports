# $NetBSD: Makefile,v 1.6 2026/09/06 10:23:33 markd Exp $

DISTNAME=	plasma-desktop-${PLASMAVER}
PKGREVISION=	4
CATEGORIES=	x11

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	KDE Plasma Desktop
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2.1 AND gnu-fdl-v1.2

.include "../../meta-pkgs/kde/plasma6.mk"

.include "../../devel/kf6-kdoctools/tools.mk"
DEPENDS+=	kf6-qqc2-desktop-style>=6.31.0:../../x11/kf6-qqc2-desktop-style
DEPENDS+=	noto-fonts>=20261001:../../fonts/noto-fonts
DEPENDS+=	noto-cjk-fonts>=20240730:../../fonts/noto-cjk-fonts
DEPENDS+=	xdg-user-dirs>=0.20:../../x11/xdg-user-dirs
DEPENDS+=	kf6-kded>=6.31.0:../../x11/kf6-kded
# PlasmaActivities starts this D-Bus service when the shell needs activities.
DEPENDS+=	plasma6-kactivitymanagerd>=6.7.5nb1:../../x11/plasma6-kactivitymanagerd

# Fcitx supplies the input-method service, Qt6 client and KF6 settings module.
DEPENDS+= fcitx5>=5.1.23nb5:../../inputmethod/fcitx5
DEPENDS+= fcitx5-qt>=5.1.16nb1:../../inputmethod/fcitx5-qt
DEPENDS+= fcitx5-configtool>=5.1.16nb1:../../inputmethod/fcitx5-configtool

USE_TOOLS+= msgmerge pkg-config

# Select the Fcitx Kimpanel D-Bus backend. Its implementation is in Fcitx.
CMAKE_CONFIGURE_ARGS+= -DBUILD_KIMPANEL_IBUS=OFF

CMAKE_CONFIGURE_ARGS+=	-DKAUTH_DBUS_DIR=${PREFIX}/share/examples/plasma-desktop
# Keep the inherited pkgsrc limits for unported tablet and X11 input backends.
# The KWin Wayland mouse and touchpad backends retain their upstream defaults.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_KCM_TABLET=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_KCM_MOUSE_X11=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_KCM_TOUCHPAD_X11=OFF

CHECK_INTERPRETER_SKIP+=	share/kconf_update/*

SUBST_CLASSES+=		xdg
SUBST_STAGE.xdg=	pre-configure
SUBST_MESSAGE.xdg=	Install via examples dir.
SUBST_FILES.xdg+=	kaccess/CMakeLists.txt
SUBST_SED.xdg+=		-e 's:{KDE_INSTALL_AUTOSTARTDIR}:{KDE_INSTALL_AUTOSTARTEXDIR}:'

MAKE_DIRS+=	${PKG_SYSCONFDIR}/xdg/autostart
CONF_FILES+=	${PREFIX}/share/examples/kde-xdg/autostart/kaccess.desktop \
		${PKG_SYSCONFDIR}/xdg/autostart/kaccess.desktop

CONF_FILES+=	${PREFIX}/share/examples/plasma-desktop/org.kde.kcontrol.kcmclock.conf \
		${PKG_SYSCONFDIR}/dbus-1/system.d/org.kde.kcontrol.kcmclock.conf

MAKE_DIRS+=		${PKG_SYSCONFDIR}/dbus-1/system.d
INSTALLATION_DIRS+=	share/examples/plasma-desktop

.include "../../mk/bsd.prefs.mk"

.if ${OPSYS} == "Linux"
pre-configure:
	ln -s /usr/lib/pkgconfig/xorg-evdev.pc ${BUILDLINK_DIR}/lib/pkgconfig/
	ln -s /usr/lib/pkgconfig/xorg-synaptics.pc ${BUILDLINK_DIR}/lib/pkgconfig/
.endif

.include "../../audio/libcanberra/buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-kitemmodels/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/kf6-knotifyconfig/buildlink3.mk"
.include "../../devel/kf6-kpackage/buildlink3.mk"
.include "../../devel/kf6-krunner/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
.include "../../devel/plasma6-plasma5support/buildlink3.mk"
.include "../../devel/qt6-qt5compat/buildlink3.mk"
.include "../../devel/SDL3/buildlink3.mk"
.include "../../fonts/fontconfig/buildlink3.mk"
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../graphics/kf6-ksvg/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../misc/kf6-attica/buildlink3.mk"
.include "../../net/kf6-knewstuff/buildlink3.mk"
.include "../../security/kf6-kauth/buildlink3.mk"
.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../sysutils/kf6-baloo/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../sysutils/plasma6-libksysguard/buildlink3.mk"
.include "../../textproc/kf6-kcodecs/buildlink3.mk"
.include "../../textproc/kf6-sonnet/buildlink3.mk"
.include "../../x11/libxkbfile/buildlink3.mk"
.include "../../x11/kf6-kglobalaccel/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../x11/kf6-kxmlgui/buildlink3.mk"
.include "../../x11/kirigami-addons/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities-stats/buildlink3.mk"
.include "../../x11/plasma6-plasma-workspace/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../x11/xcb-util-cursor/buildlink3.mk"
.include "../../x11/xkeyboard-config/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
