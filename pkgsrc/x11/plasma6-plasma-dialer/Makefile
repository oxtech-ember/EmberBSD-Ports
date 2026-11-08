# $NetBSD$

DISTNAME=	plasma-dialer-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://invent.kde.org/plasma-mobile/plasma-dialer
COMMENT=	Plasma dialer client and telephony D-Bus front end
LICENSE=	gnu-gpl-v2 AND gnu-gpl-v3 AND gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/plasma6.mk"

# The client and the modem front end are built. Autostart and D-Bus
# activation files are moved out of the session directories so installing
# the package does not start the modem daemon or place a call.

USE_TOOLS+=	msgmerge pkg-config

# The cross qtdeclarative buildlink is a tool dependency. check-shlibs
# still requires the target package on the runtime dependency list.
DEPENDS+=	qt6-qtdeclarative>=6.12.0:../../lang/qt6-qtdeclarative

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING:BOOL=OFF

post-install:
	${MKDIR} ${DESTDIR}${PREFIX}/share/examples/plasma6-plasma-dialer
	for f in \
		${DESTDIR}${PREFIX}/share/autostart/org.kde.modem.daemon.desktop \
		${DESTDIR}${PREFIX}/etc/xdg/autostart/org.kde.modem.daemon.desktop \
		${DESTDIR}${PREFIX}/share/autostart/org.kde.telephony.daemon.desktop \
		${DESTDIR}${PREFIX}/etc/xdg/autostart/org.kde.telephony.daemon.desktop \
		${DESTDIR}${PREFIX}/share/dbus-1/services/org.kde.modemdaemon.service \
		${DESTDIR}${PREFIX}/share/dbus-1/services/org.kde.telephony.service; do \
		if [ -f "$$f" ]; then \
			${MV} "$$f" ${DESTDIR}${PREFIX}/share/examples/plasma6-plasma-dialer/; \
		fi; \
	done

.include "../../audio/callaudiod/buildlink3.mk"
.include "../../comms/libphonenumber/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-kpeople/buildlink3.mk"
.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../misc/kf6-kcontacts/buildlink3.mk"
.include "../../multimedia/qt6-qtmultimedia/buildlink3.mk"
.include "../../net/modemmanager-qt/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kirigami-addons/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
