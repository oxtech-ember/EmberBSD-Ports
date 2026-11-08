# $NetBSD$

DISTNAME=	xdg-desktop-portal-kde-${PLASMAVER}
CATEGORIES=	misc

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Backend implementation for xdg-desktop-portal using Qt/KF6
LICENSE=	gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/plasma6.mk"

# The backend is built. Its D-Bus activation file and systemd user unit
# are moved out of the service directories so installing the package does
# not start the portal.

USE_TOOLS+=	msgmerge pkg-config

USE_CXX_FEATURES+=	c++23

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING:BOOL=OFF

post-install:
	${MKDIR} ${DESTDIR}${PREFIX}/share/examples/plasma6-xdg-desktop-portal-kde
	for f in \
		${DESTDIR}${PREFIX}/share/dbus-1/services/org.freedesktop.impl.portal.desktop.kde.service \
		${DESTDIR}${PREFIX}/lib/systemd/user/plasma-xdg-desktop-portal-kde.service \
		${DESTDIR}${PREFIX}/share/systemd/user/plasma-xdg-desktop-portal-kde.service; do \
		if [ -f "$$f" ]; then \
			${MV} "$$f" ${DESTDIR}${PREFIX}/share/examples/plasma6-xdg-desktop-portal-kde/; \
		fi; \
	done

DEPENDS+=	qt6-qtdeclarative>=6.12.0:../../lang/qt6-qtdeclarative

.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/kf6-kservice/buildlink3.mk"
.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/plasma6-kwayland/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../misc/kf6-kstatusnotifieritem/buildlink3.mk"
.include "../../multimedia/pipewire/buildlink3.mk"
.include "../../multimedia/plasma6-kpipewire/buildlink3.mk"
.include "../../x11/kf6-kglobalaccel/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
