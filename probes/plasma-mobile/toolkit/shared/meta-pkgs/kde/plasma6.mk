# $NetBSD: plasma6.mk,v 1.4 2026/09/06 10:23:28 markd Exp $
# Origin: pkgsrc, adapted by EmberBSD (AI-assisted).
.include "../../mk/bsd.prefs.mk"
PLASMAVER?= 6.7.5
.if ${PLASMAVER} != "6.7.5"
PKG_FAIL_REASON+= "The common toolkit requires PLASMAVER=6.7.5"
.endif
_EMBERBSD_PLASMA6_RECIPES= devel/plasma6-kwayland time/plasma6-knighttime \
    x11/plasma6-kdecoration x11/plasma6-kglobalacceld x11/plasma6-layer-shell-qt \
    graphics/plasma6-aurorae \
    graphics/plasma6-breeze \
    x11/plasma6-kscreenlocker \
    x11/plasma6-libkscreen \
    x11/plasma6-libplasma \
    x11/plasma6-plasma-activities x11/plasma6-kwin sysutils/plasma6-milou \
    sysutils/plasma6-libksysguard devel/plasma6-plasma5support \
    x11/plasma6-plasma-activities-stats x11/plasma6-plasma-workspace
.if empty(_EMBERBSD_PLASMA6_RECIPES:M${PKGPATH})
PKG_FAIL_REASON+= "Plasma 6 recipe ${PKGPATH} is not prepared in the common toolkit"
.endif
GCC_REQD+= 16.2
CATEGORIES+= kde
MASTER_SITES= ${MASTER_SITE_KDE:=plasma/${PLASMAVER}/}
EXTRACT_SUFX= .tar.xz
PKGNAME?= plasma6-${DISTNAME}
USE_CXX_FEATURES+= c++20
.include "../../meta-pkgs/kde/Makefile.common"

# ECM queries native qtpaths. Its directories must never enter target packages.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Imported pkg-config targets require real target include/library directories.
CONFIGURE_ENV+= PKG_CONFIG_SYSROOT_DIR=${CROSS_DESTDIR:Q}
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_APP_TEMPLATES=ON
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTPLUGINDIR=qt6/plugins
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QMLDIR=qt6/qml
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTMETATYPESDIR=qt6/metatypes
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTQCHDIR=qt6/doc
.endif
