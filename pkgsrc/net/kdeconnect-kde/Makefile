# $NetBSD$

DISTNAME=	kdeconnect-kde-25.08.3
CATEGORIES=	net
MASTER_SITES=	https://download.kde.org/stable/release-service/25.08.3/src/
EXTRACT_SUFX=	.tar.xz

HOMEPAGE=	https://kdeconnect.kde.org/
COMMENT=	KDE Connect client libraries and interface
LICENSE=	gnu-gpl-v2 AND gnu-gpl-v3

.include "../../devel/cmake/build.mk"

USE_LANGUAGES=	c c++
USE_CXX_FEATURES+=	c++20
USE_TOOLS+=	msgmerge pkg-config

DEPENDS+=	qt6-qtdeclarative>=6.12.0:../../lang/qt6-qtdeclarative

# PulseAudio plugins are not built. Qt Bluetooth is not in this sysroot,
# so the Bluetooth backend is not built. The daemon autostart and D-Bus
# activation file are moved aside so installing the package does not
# start pairing or open a listener.
CMAKE_CONFIGURE_ARGS+=	-DWITH_PULSEAUDIO:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DBLUETOOTH_ENABLED:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DKDE_INSTALL_QMLDIR=qt6/qml
CMAKE_CONFIGURE_ARGS+=	-DKDE_INSTALL_QTPLUGINDIR=qt6/plugins

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CMAKE_CONFIGURE_ARGS+=	-DWayland_Client_LIBRARY=${CROSS_DESTDIR}/usr/pkg/lib/libwayland-client.so
CMAKE_CONFIGURE_ARGS+=	-DWayland_Client_INCLUDE_DIR=${CROSS_DESTDIR}/usr/pkg/include
CMAKE_CONFIGURE_ARGS+=	-DWayland_Cursor_LIBRARY=${CROSS_DESTDIR}/usr/pkg/lib/libwayland-cursor.so
CMAKE_CONFIGURE_ARGS+=	-DWayland_Cursor_INCLUDE_DIR=${CROSS_DESTDIR}/usr/pkg/include
CMAKE_CONFIGURE_ARGS+=	-DWaylandProtocols_DATADIR=${CROSS_DESTDIR}/usr/pkg/share/wayland-protocols
.endif

post-install:
	${MKDIR} ${DESTDIR}${PREFIX}/share/examples/kdeconnect-kde
	for f in \
		${DESTDIR}${PREFIX}/share/autostart/org.kde.kdeconnect.daemon.desktop \
		${DESTDIR}${PREFIX}/etc/xdg/autostart/org.kde.kdeconnect.daemon.desktop \
		${DESTDIR}${PREFIX}/share/dbus-1/services/org.kde.kdeconnect.service; do \
		if [ -f "$$f" ]; then \
			${MV} "$$f" ${DESTDIR}${PREFIX}/share/examples/kdeconnect-kde/; \
		fi; \
	done

.include "../../x11/kf6-qqc2-desktop-style/buildlink3.mk"

.include "../../devel/kf6-kcolorscheme/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-kitemmodels/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/kf6-kpackage/buildlink3.mk"
.include "../../devel/kf6-kpeople/buildlink3.mk"
.include "../../devel/kf6-kservice/buildlink3.mk"
.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../misc/kf6-kstatusnotifieritem/buildlink3.mk"
.include "../../multimedia/qt6-qtmultimedia/buildlink3.mk"
.include "../../sysutils/kf6-solid/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/kirigami-addons/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXtst/buildlink3.mk"
.include "../../x11/libfakekey/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
