# $NetBSD$

DISTNAME=	spacebar-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://invent.kde.org/plasma-mobile/spacebar
COMMENT=	Plasma SMS client
LICENSE=	gnu-gpl-v2 AND gnu-gpl-v3 AND gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/plasma6.mk"

# The client is built. The daemon autostart file is moved out of the
# session directory so installing the package does not start it or send SMS.

USE_TOOLS+=	msgmerge pkg-config

# The cross qtdeclarative buildlink is a tool dependency. check-shlibs
# still requires the target package on the runtime dependency list.
DEPENDS+=	qt6-qtdeclarative>=6.12.0:../../lang/qt6-qtdeclarative

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING:BOOL=OFF

post-install:
	${MKDIR} ${DESTDIR}${PREFIX}/share/examples/plasma6-spacebar
	for f in \
		${DESTDIR}${PREFIX}/share/autostart/org.kde.spacebar.daemon.desktop \
		${DESTDIR}${PREFIX}/etc/xdg/autostart/org.kde.spacebar.daemon.desktop; do \
		if [ -f "$$f" ]; then \
			${MV} "$$f" ${DESTDIR}${PREFIX}/share/examples/plasma6-spacebar/; \
		fi; \
	done

.include "../../comms/libphonenumber/buildlink3.mk"
.include "../../databases/futuresql/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-kpeople/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/qcoro/buildlink3.mk"
.include "../../misc/kf6-kcontacts/buildlink3.mk"
.include "../../net/libcares/buildlink3.mk"
.include "../../net/modemmanager-qt/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../www/curl/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kirigami-addons/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
