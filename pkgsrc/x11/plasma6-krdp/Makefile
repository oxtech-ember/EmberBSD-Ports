# $NetBSD$

DISTNAME=	krdp-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://invent.kde.org/plasma/krdp
COMMENT=	Remote desktop server library for Plasma
LICENSE=	gnu-lgpl-v2 AND gnu-gpl-v2 AND gnu-lgpl-v3 AND gnu-gpl-v3

.include "../../meta-pkgs/kde/plasma6.mk"

# The library and the server binary are built. The server is not started
# and no port is opened. Systemd unit files are kept as examples.

USE_TOOLS+=	msgmerge pkg-config

CMAKE_CONFIGURE_ARGS+=	-DBUILD_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DFreeRDP_DIR=${EMBERBSD_CROSS_SYSROOT}/usr/pkg/lib/cmake/FreeRDP3
CMAKE_CONFIGURE_ARGS+=	-DWinPR_DIR=${EMBERBSD_CROSS_SYSROOT}/usr/pkg/lib/cmake/WinPR3
CMAKE_CONFIGURE_ARGS+=	-DFreeRDP-Server_DIR=${EMBERBSD_CROSS_SYSROOT}/usr/pkg/lib/cmake/FreeRDP-Server3
CMAKE_CONFIGURE_ARGS+=	-DPAM_INCLUDE_DIR=${EMBERBSD_CROSS_SYSROOT}/usr/include
CMAKE_CONFIGURE_ARGS+=	-DPAM_LIBRARY=${EMBERBSD_CROSS_SYSROOT}/usr/lib/libpam.so

post-install:
	${MKDIR} ${DESTDIR}${PREFIX}/share/examples/plasma6-krdp
	if [ -f ${DESTDIR}${PREFIX}/lib/systemd/user/app-org.kde.krdpserver.service ]; then \
		${MV} ${DESTDIR}${PREFIX}/lib/systemd/user/app-org.kde.krdpserver.service \
			${DESTDIR}${PREFIX}/share/examples/plasma6-krdp/ ; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/lib/systemd/user-preset/00-krdp.preset ]; then \
		${MV} ${DESTDIR}${PREFIX}/lib/systemd/user-preset/00-krdp.preset \
			${DESTDIR}${PREFIX}/share/examples/plasma6-krdp/ ; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/share/applications/org.kde.krdpserver.desktop ]; then \
		${MV} ${DESTDIR}${PREFIX}/share/applications/org.kde.krdpserver.desktop \
			${DESTDIR}${PREFIX}/share/examples/plasma6-krdp/ ; \
	fi

.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../misc/kf6-kstatusnotifieritem/buildlink3.mk"
.include "../../multimedia/plasma6-kpipewire/buildlink3.mk"
.include "../../net/freerdp3/buildlink3.mk"
.include "../../security/qt6-qtkeychain/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/libei/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
