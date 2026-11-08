# $NetBSD$

DISTNAME=	drkonqi-${PLASMAVER}
CATEGORIES=	sysutils

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Crash handler dialog for KDE applications
LICENSE=	gnu-gpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

# Without libsystemd the coredumpd launcher is not built. The dialog and
# the GDB backend remain. Do not install this package into a live session.

USE_TOOLS+=	msgmerge pkg-config

# pygdbmi, psutil and sentry-sdk are optional GDB helpers fetched by pip.
# Leave them out. The dialog still launches GDB with the shipped preamble.
CMAKE_CONFIGURE_ARGS+=	-DWITH_PYTHON_VENDORING=OFF

post-extract:
	${CP} ${FILESDIR}/memoryfence_portable.cpp ${WRKSRC}/src/systemd/memoryfence_portable.cpp
	${CP} ${FILESDIR}/memorypressure_portable.cpp ${WRKSRC}/src/systemd/memorypressure_portable.cpp

.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-kidletime/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/kf6-kservice/buildlink3.mk"
.include "../../misc/kf6-kstatusnotifieritem/buildlink3.mk"
.include "../../security/kf6-kwallet/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../textproc/kf6-syntax-highlighting/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
