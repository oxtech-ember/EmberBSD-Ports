# $NetBSD: options.mk,v 1.5 2023/09/30 08:05:48 adam Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.qt6-qtbase
PKG_SUPPORTED_OPTIONS+=	dbus gtk3
PKG_SUGGESTED_OPTIONS+=	dbus

.include "../../mk/bsd.fast.prefs.mk"

# Native generators for cross builds: moc, rcc, uic and their CMake packages.
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PKG_SUPPORTED_OPTIONS+=	host-tools
.if ${OPSYS} == "Linux"
PKG_SUPPORTED_OPTIONS+=	headless-generators
.endif
.endif

# QtQuick software rendering supports native Linux and NetBSD cross builds.
.if (${OPSYS} == "Linux" && ${USE_CROSS_COMPILE:Uno:tl} != "yes") || \
    (${OPSYS} == "NetBSD" && ${USE_CROSS_COMPILE:Uno:tl} == "yes")
PKG_SUPPORTED_OPTIONS+=	software-rendering
.endif

.if ${OPSYS} != "Darwin"
PKG_SUPPORTED_OPTIONS+=	cups
PKG_SUGGESTED_OPTIONS+=	cups
.endif

.include "../../mk/bsd.options.mk"

PLIST_VARS+=		cups dbus gtk3 opengl vulkan

# Native GUI generators without XCB: select software-rendering and
# headless-generators; do not select gtk3 or host-tools.
.if !empty(PKG_OPTIONS:Mheadless-generators)
.if ${OPSYS} != "Linux" || ${USE_CROSS_COMPILE:Uno:tl} == "yes" || empty(PKG_OPTIONS:Msoftware-rendering)
PKG_FAIL_REASON+= "headless-generators requires native Linux software-rendering"
.endif
.if !empty(PKG_OPTIONS:Mgtk3) || !empty(PKG_OPTIONS:Mhost-tools)
PKG_FAIL_REASON+= "headless-generators excludes gtk3 and host-tools"
.endif
CMAKE_CONFIGURE_ARGS+= -DFEATURE_xcb:BOOL=OFF -DFEATURE_xlib:BOOL=OFF
CMAKE_CONFIGURE_ARGS+= -DFEATURE_wayland:BOOL=OFF -DFEATURE_qtwaylandscanner:BOOL=OFF
.endif

.if !empty(PKG_OPTIONS:Msoftware-rendering)
.if (${OPSYS} != "Linux" && ${OPSYS} != "NetBSD") || \
    (${OPSYS} == "Linux" && ${USE_CROSS_COMPILE:Uno:tl} == "yes") || \
    (${OPSYS} == "NetBSD" && ${USE_CROSS_COMPILE:Uno:tl} != "yes")
PKG_FAIL_REASON+=	"software-rendering supports native Linux and NetBSD cross builds"
.endif
.if !empty(PKG_OPTIONS:Mhost-tools)
PKG_FAIL_REASON+=	"software-rendering cannot be combined with the host-tools option"
.endif
CONFIGURE_ARGS+=	-no-opengl -no-feature-egl -no-feature-eglfs
CONFIGURE_ARGS+=	-no-feature-eglfs_egldevice -no-feature-vulkan
CMAKE_CONFIGURE_ARGS+=	-DFEATURE_egl:BOOL=OFF -DFEATURE_eglfs:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DFEATURE_eglfs_egldevice:BOOL=OFF -DFEATURE_vulkan:BOOL=OFF
.else
PLIST.opengl=	yes
.if ${OPSYS} != "Darwin"
PLIST.vulkan=	yes
.endif
.endif

.if !empty(PKG_OPTIONS:Mhost-tools)
.  for _opt_ in cups dbus gtk3 software-rendering
.    if !empty(PKG_OPTIONS:M${_opt_})
PKG_FAIL_REASON+=	"The host-tools option excludes the ${_opt_} option"
.    endif
.  endfor
PLIST_SRC=		${PKGDIR}/PLIST.host-tools
CONFIGURE_ARGS+=	-no-gui -no-widgets -no-accessibility
CONFIGURE_ARGS+=	-no-icu -no-libproxy -no-openssl -no-glib
CONFIGURE_ARGS+=	-no-feature-network -no-feature-sql -no-feature-testlib
CONFIGURE_ARGS+=	-qt-harfbuzz -qt-libjpeg -qt-libpng -qt-libmd4c
.endif

.if !empty(PKG_OPTIONS:Mcups)
.  include "../../print/libcups/buildlink3.mk"
CONFIGURE_ARGS+=	-cups
PLIST.cups=		yes
.else
CONFIGURE_ARGS+=	-no-cups
.endif

.if !empty(PKG_OPTIONS:Mdbus)
# Use lib/dbus-1.0/include/dbus/dbus-arch-deps.h from sysutils/dbus
USE_DBUS-ARCH-DEPS_H=	yes
.include "../../sysutils/dbus/buildlink3.mk"
CONFIGURE_ARGS+=	-dbus-linked
PLIST.dbus=		yes
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6DBus.pc
.else
CONFIGURE_ARGS+=	-no-dbus
.endif

.if !empty(PKG_OPTIONS:Mgtk3)
.  include "../../x11/gtk3/buildlink3.mk"
CONFIGURE_ARGS+=	-gtk
PLIST.gtk3=		yes
.else
CONFIGURE_ARGS+=	-no-gtk
.endif
