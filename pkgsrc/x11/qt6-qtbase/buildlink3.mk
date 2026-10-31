# $NetBSD: buildlink3.mk,v 1.29 2026/09/02 19:05:31 wiz Exp $

BUILDLINK_TREE+=	qt6-qtbase

.if !defined(QT6_QTBASE_BUILDLINK3_MK)
QT6_QTBASE_BUILDLINK3_MK:=

.include "../../mk/bsd.fast.prefs.mk"

BUILDLINK_API_DEPENDS.qt6-qtbase+=	qt6-qtbase>=6.12.0
BUILDLINK_ABI_DEPENDS.qt6-qtbase+=	qt6-qtbase>=6.12.0
BUILDLINK_PKGSRCDIR.qt6-qtbase?=	../../x11/qt6-qtbase

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
BUILDLINK_API_DEPENDS.qt6-qtbase+= qt6-qtbase>=6.12.0nb8
BUILDLINK_ABI_DEPENDS.qt6-qtbase+= qt6-qtbase>=6.12.0nb8
# The installed image needs the runtime; CMake consumers also need the SDK
# in the build-host sysroot. BUILD_DEPENDS remains a target cross dependency.
.include "../../x11/qt6-qtbase-devel/buildlink3.mk"
# Qt libraries need other Qt libraries from qt6/lib through their RPATH.
# The cross GNU ld has no sysroot, so it resolves them only through
# rpath-link.
LDFLAGS+=	-Wl,-rpath-link,${CROSS_DESTDIR}/usr/pkg/qt6/lib
# Consumers run moc and rcc from the native package selected there.
.include "../../x11/qt6-qtbase/host-tools.mk"
.else
BUILDLINK_API_DEPENDS.qt6-qtbase+= qt6-qtbase>=6.12.0nb15
BUILDLINK_ABI_DEPENDS.qt6-qtbase+= qt6-qtbase>=6.12.0nb15
.endif

BUILDLINK_INCDIRS.qt6-qtbase+=	qt6/include
BUILDLINK_LIBDIRS.qt6-qtbase+=	qt6/lib
BUILDLINK_LIBDIRS.qt6-qtbase+=	qt6/plugins

# XXX This is wrong -- we should get build-time executables via
# TOOL_DEPENDS, not via buildlink3.  See
# https://mail-index.netbsd.org/tech-pkg/2025/01/12/msg030374.html for
# details.  We do this anyway for now as an expedient workaround for a
# bug unearthed by hiding files in LOCALBASE from cmake and limiting it
# to buildlink3.
BUILDLINK_FILES.qt6-qtbase+=	qt6/bin/*
BUILDLINK_FILES.qt6-qtbase+=	qt6/libexec/*
BUILDLINK_FILES.qt6-qtbase+=	qt6/plugins/*/*/*/*
# referred to from qt6/lib/cmake/Qt6ExampleIconsPrivate/Qt6ExampleIconsPrivateTargets.cmake
BUILDLINK_FILES.qt6-qtbase+=	qt6/lib/objects-Release/ExampleIconsPrivate_resources_1/.qt/rcc/qrc_example_icons_init.cpp.o

# \todo Fix duplication with prefix coded in Makefile.common
QTDIR=		${BUILDLINK_PREFIX.qt6-qtbase}/qt6
CMAKE_PREFIX_PATH+=	${QTDIR}

CONFIGURE_ENV+=	QTDIR=${QTDIR}
MAKE_ENV+=	QTDIR=${QTDIR}

PTHREAD_OPTS+=	require

pkgbase := qt6-qtbase
.include "../../mk/pkg-build-options.mk"

# Some Qt6 packages install extra files
# if the dbus option is enabled in qtbase.
PLIST_VARS+=	qt6dbus
.if ${PKG_BUILD_OPTIONS.qt6-qtbase:Mdbus}
.include "../../sysutils/dbus/buildlink3.mk"
PLIST.qt6dbus=	yes
.endif

.if ${PKG_BUILD_OPTIONS.qt6-qtbase:Mcups}
.include "../../print/libcups/buildlink3.mk"
.endif

.include "../../converters/libiconv/buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../devel/pcre2/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
# The host-tools build has no GUI, network, SQL or ICU dependencies.
.if !${PKG_BUILD_OPTIONS.qt6-qtbase:Mhost-tools}
.include "../../databases/sqlite3/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../fonts/harfbuzz/buildlink3.mk"
.include "../../graphics/freetype2/buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../www/libproxy/buildlink3.mk"
BUILDLINK_API_DEPENDS.libpsl+= libpsl>=0.23.3nb2
.include "../../www/libpsl/buildlink3.mk"
.include "../../mk/jpeg.buildlink3.mk"
.if ${OPSYS} != "Darwin"
.include "../../fonts/fontconfig/buildlink3.mk"
.include "../../graphics/glu/buildlink3.mk"
.include "../../graphics/vulkan-headers/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.include "../../x11/xcb-util/buildlink3.mk"
.include "../../x11/xcb-util-image/buildlink3.mk"
.include "../../x11/xcb-util-keysyms/buildlink3.mk"
.include "../../x11/xcb-util-renderutil/buildlink3.mk"
.include "../../x11/xcb-util-wm/buildlink3.mk"
.include "../../x11/libSM/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXcursor/buildlink3.mk"
.include "../../x11/libXft/buildlink3.mk"
.include "../../x11/libXi/buildlink3.mk"
.include "../../x11/libXmu/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libXrender/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.endif
.endif
.include "../../mk/atomic64.mk"
.endif	# QT6_QTBASE_BUILDLINK3_MK

BUILDLINK_TREE+=	-qt6-qtbase
