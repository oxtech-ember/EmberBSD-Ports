# $NetBSD: Makefile,v 1.25 2016/01/10 20:01:05 markd Exp $

DISTNAME=	kwin-${PLASMAVER}
PKGREVISION=	3
CATEGORIES=	x11

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Wayland compositor for KDE Plasma Desktops
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

# Vulkan-Hpp loads libvulkan.so at runtime; headers do not supply the loader.
DEPENDS+=	vulkan-loader>=1.4.357.0:../../graphics/vulkan-loader

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Build this native generator with cross/build-kwin-scanner.sh first.
CMAKE_CONFIGURE_ARGS+= -DQTWAYLANDSCANNER_KDE_EXECUTABLE=${EMBERBSD_KF6_HOST_TOOLING}/bin/qtwaylandscanner_kde
pre-configure:
	${TEST} -x ${EMBERBSD_KF6_HOST_TOOLING}/bin/qtwaylandscanner_kde
.endif

# std::ranges::to<QList>
USE_CXX_FEATURES+=	c++23

.include "../../devel/kf6-kdoctools/buildlink3.mk"

USE_TOOLS+=	msgmerge pkg-config
.include "../../lang/python/tool.mk"


# generation of module.moc fails when ${PREFIX}/include in the moc include path
SUBST_CLASSES+=		fix-moc
SUBST_STAGE.fix-moc=	post-configure
SUBST_MESSAGE.fix-moc=	Cleaning up MOC includes
SUBST_FILES.fix-moc=	_KDE_build/*/CMakeFiles/*_autogen.dir/AutogenInfo.json
SUBST_NOOP_OK.fix-moc=	yes
SUBST_SED.fix-moc=	-e 's;"${PREFIX}/include",;;g'

.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-kdeclarative/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-kservice/buildlink3.mk"
.include "../../devel/libopeninput/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/plasma6-kwayland/buildlink3.mk"
.include "../../devel/qt6-qt5compat/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../graphics/kf6-ksvg/buildlink3.mk"
.include "../../graphics/lcms2/buildlink3.mk"
.include "../../graphics/plasma6-aurorae/buildlink3.mk"
.include "../../graphics/plasma6-breeze/buildlink3.mk"
.include "../../graphics/qt6-qtsvg/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../misc/qt6-qtsensors/buildlink3.mk"
.include "../../net/kf6-knewstuff/buildlink3.mk"
.include "../../security/kf6-kauth/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../time/plasma6-knighttime/buildlink3.mk"
.include "../../x11/kf6-kconfigwidgets/buildlink3.mk"
.include "../../x11/kf6-kglobalaccel/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/kf6-kxmlgui/buildlink3.mk"
.include "../../x11/libdisplay-info/buildlink3.mk"
.include "../../x11/libxcvt/buildlink3.mk"
.include "../../x11/plasma6-kdecoration/buildlink3.mk"
.include "../../x11/plasma6-kglobalacceld/buildlink3.mk"
.include "../../x11/plasma6-kscreenlocker/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../x11/xcb-util-cursor/buildlink3.mk"
.include "../../devel/kf6-kcolorscheme/buildlink3.mk"
.include "../../devel/kf6-kidletime/buildlink3.mk"
.include "../../devel/kf6-kpackage/buildlink3.mk"
.include "../../devel/kf6-krunner/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../graphics/libepoxy/buildlink3.mk"
.include "../../graphics/vulkan-headers/buildlink3.mk"
.include "../../x11/libdrm/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
