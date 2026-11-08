# $NetBSD$

DISTNAME=	kup-0.10.0
CATEGORIES=	sysutils
MASTER_SITES=	https://download.kde.org/stable/kup/
EXTRACT_SUFX=	.tar.xz

HOMEPAGE=	https://apps.kde.org/kup/
COMMENT=	Backup scheduler for the Plasma desktop
LICENSE=	gnu-gpl-v2

CMAKE_CONFIGURE_ARGS+=	-DQT_MAJOR_VERSION=6

USE_LANGUAGES=	c c++
USE_TOOLS+=	msgmerge pkg-config

# kup-daemon.desktop would start the backup daemon at the next login.
post-install:
	${MKDIR} ${DESTDIR}${PREFIX}/share/examples/kde-xdg/autostart
	${MV} ${DESTDIR}${PREFIX}/etc/xdg/autostart/kup-daemon.desktop \
		${DESTDIR}${PREFIX}/share/examples/kde-xdg/autostart/

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../devel/libgit2/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kidletime/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/plasma6-plasma5support/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../sysutils/kf6-solid/buildlink3.mk"
.include "../../x11/kf6-kjobwidgets/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../x11/kf6-kxmlgui/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
