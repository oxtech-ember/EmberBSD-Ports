# $NetBSD: plasma6.mk,v 1.4 2026/09/06 10:23:28 markd Exp $
# Origin: pkgsrc, adapted by EmberBSD (AI-assisted).
.include "../../mk/bsd.prefs.mk"
PLASMAVER?= 6.8.2
.if ${PLASMAVER} != "6.8.2"
PKG_FAIL_REASON+= "The common toolkit requires PLASMAVER=6.8.2"
.endif
_EMBERBSD_PLASMA6_RECIPES= audio/plasma6-plasma-pa devel/plasma6-kwayland time/plasma6-knighttime \
    x11/plasma6-kdecoration x11/plasma6-kglobalacceld x11/plasma6-layer-shell-qt \
    graphics/plasma6-aurorae \
    graphics/plasma6-breeze \
    x11/plasma6-kscreenlocker \
    x11/plasma6-libkscreen \
    x11/plasma6-libplasma \
    x11/plasma6-plasma-activities x11/plasma6-kwin x11/plasma6-kwin-qtwaylandscanner sysutils/plasma6-milou \
    sysutils/plasma6-libksysguard devel/plasma6-plasma5support \
    x11/plasma6-plasma-activities-stats x11/plasma6-union x11/plasma6-plasma-nano x11/plasma6-plasma-mobile \
    x11/plasma6-plasma-workspace \
    x11/plasma6-plasma-desktop x11/plasma6-kactivitymanagerd
.if empty(_EMBERBSD_PLASMA6_RECIPES:M${PKGPATH})
PKG_FAIL_REASON+= "Plasma 6 recipe ${PKGPATH} is not prepared in the common toolkit"
.endif
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
# Plasma 6.8 resolves Qt6WaylandClient's third-party Wayland dependency with
# ECM's FindWayland inside the Qt package context, where the pkg-config hints
# do not reach the fallback find_library/find_path calls. Seed the ECM cache
# variables from the cross sysroot so the Qt-internal lookups cannot fail.
CMAKE_CONFIGURE_ARGS+= -DWayland_Client_LIBRARY=${CROSS_DESTDIR}/usr/pkg/lib/libwayland-client.so
CMAKE_CONFIGURE_ARGS+= -DWayland_Client_INCLUDE_DIR=${CROSS_DESTDIR}/usr/pkg/include
CMAKE_CONFIGURE_ARGS+= -DWayland_Server_LIBRARY=${CROSS_DESTDIR}/usr/pkg/lib/libwayland-server.so
CMAKE_CONFIGURE_ARGS+= -DWayland_Server_INCLUDE_DIR=${CROSS_DESTDIR}/usr/pkg/include
CMAKE_CONFIGURE_ARGS+= -DWayland_Cursor_LIBRARY=${CROSS_DESTDIR}/usr/pkg/lib/libwayland-cursor.so
CMAKE_CONFIGURE_ARGS+= -DWayland_Cursor_INCLUDE_DIR=${CROSS_DESTDIR}/usr/pkg/include
CMAKE_CONFIGURE_ARGS+= -DWayland_Egl_LIBRARY=${CROSS_DESTDIR}/usr/pkg/lib/libwayland-egl.so
CMAKE_CONFIGURE_ARGS+= -DWayland_Egl_INCLUDE_DIR=${CROSS_DESTDIR}/usr/pkg/include
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_APP_TEMPLATES=ON
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTPLUGINDIR=qt6/plugins
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QMLDIR=qt6/qml
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTMETATYPESDIR=qt6/metatypes
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTQCHDIR=qt6/doc
.endif
