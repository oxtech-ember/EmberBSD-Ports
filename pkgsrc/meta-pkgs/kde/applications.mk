# $NetBSD: applications.mk,v 1.12 2026/09/06 11:02:43 markd Exp $

KAPPSVER?=	26.08.0
CATEGORIES+=	kde
MASTER_SITES?=	${MASTER_SITE_KDE:=release-service/${KAPPSVER}/src/}
EXTRACT_SUFX?=	.tar.xz

.if !defined(STILL_KF5)
USE_CXX_FEATURES+=	c++20
.endif

.include "../../meta-pkgs/kde/Makefile.common"

# Origin: EmberBSD (AI-assisted). Cross builds must keep ECM's Qt install
# directories inside the target prefix; without these arguments ECM derives
# them from QT_HOST_PATH and stages QML modules under absolute host paths.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CONFIGURE_ENV+= PKG_CONFIG_SYSROOT_DIR=${CROSS_DESTDIR:Q}
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_APP_TEMPLATES=ON
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTPLUGINDIR=qt6/plugins
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QMLDIR=qt6/qml
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTMETATYPESDIR=qt6/metatypes
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTQCHDIR=qt6/doc
# The recipes name the full kf6-kdoctools as a tool. Its native build needs
# KI18n, QML and the Qt GUI stack, which the native host-tools Qt does not
# provide. A cross build only runs meinproc6, checkXML6 and
# docbookl10nhelper, so it takes them from kf6-kdoctools-generators.
EMBERBSD_CROSS_TOOL_REPLACE+= devel/kf6-kdoctools
.endif
