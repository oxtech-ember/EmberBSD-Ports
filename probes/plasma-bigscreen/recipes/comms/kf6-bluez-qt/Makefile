# $NetBSD$
# Origin: EmberBSD (AI-assisted). Source candidate; package QA remains pending.

DISTNAME=	bluez-qt-6.31.0
PKGNAME=	kf6-${DISTNAME}
CATEGORIES=	comms kde
MASTER_SITES=	${MASTER_SITE_KDE:=frameworks/6.31/}
EXTRACT_SUFX=	.tar.xz

HOMEPAGE=	https://api.kde.org/bluez-qt/
COMMENT=	Qt clients for the BlueZ 5 D-Bus interfaces
LICENSE=	gnu-lgpl-v2.1 OR gnu-lgpl-v3

USE_LANGUAGES=	c c++
USE_CXX_FEATURES=	c++20
USE_TOOLS+=	pkg-config
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=ON
# Keep ECM's platform check. The source explicitly describes client support.
CMAKE_CONFIGURE_ARGS+= -DKF_IGNORE_PLATFORM_CHECK=OFF

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if empty(EMBERBSD_QT_HOST_PATH:M/*) || !exists(${EMBERBSD_QT_HOST_PATH}/libexec/moc)
PKG_FAIL_REASON+= "Select the matching common native Qt generators with EMBERBSD_QT_HOST_PATH"
.endif
CMAKE_CONFIGURE_ARGS+= -DQT_HOST_PATH=${EMBERBSD_QT_HOST_PATH}
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTPLUGINDIR=qt6/plugins
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QMLDIR=qt6/qml
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTMETATYPESDIR=qt6/metatypes
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTQCHDIR=qt6/doc
CONFIGURE_ENV+= PKG_CONFIG_SYSROOT_DIR=${CROSS_DESTDIR:Q}
.endif

BUILDLINK_API_DEPENDS.extra-cmake-modules+= extra-cmake-modules>=6.31.0
.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
