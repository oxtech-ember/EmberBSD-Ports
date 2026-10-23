# $NetBSD: options.mk,v 1.5 2026/05/25 15:50:45 bsiegert Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.at-spi2-core

#
# Make dbus optional. Note that turning dbus off does not actually
# make at-spi2 work without dbus; it tells it to build only atk, and
# makes this package approximately equivalent to the standalone atk
# package that used to exist. This in turn avoids incurring a
# mandatory dbus dependency for a large number of applications that
# never previously had one.
#
# However, anything that actually needs at-spi2 will not work with
# dbus turned off, and probably not build either.
#
PKG_SUPPORTED_OPTIONS=	dbus introspection
PKG_SUGGESTED_OPTIONS=	dbus introspection

.include "../../mk/bsd.options.mk"

PLIST_VARS+=	dbus
PLIST_VARS+=	introspection

.if ${PKG_OPTIONS:Mdbus}
PLIST.dbus=	yes

MESON_ARGS+=			-Duse_systemd=false
MESON_ARGS+=			-Ddefault_bus=dbus-daemon

#
# These files only get installed when dbus is in use.
#
MAKE_DIRS+=	${PKG_SYSCONFDIR}/at-spi2
CONF_FILES=	${EGDIR}/at-spi2/accessibility.conf \
		${PKG_SYSCONFDIR}/at-spi2/accessibility.conf
CONF_FILES+=	${EGDIR}/xdg/autostart/at-spi-dbus-bus.desktop \
		${PKG_SYSCONFDIR}/xdg/autostart/at-spi-dbus-bus.desktop
post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${EGDIR}/xdg/autostart
	${MV} ${DESTDIR}${PKG_SYSCONFDIR}/xdg/autostart/at-spi-dbus-bus.desktop \
	      ${DESTDIR}${EGDIR}/xdg/autostart/at-spi-dbus-bus.desktop

.include "../../sysutils/dbus/buildlink3.mk"

.else
MESON_ARGS+=	-Datk_only=true
.endif

.if ${PKG_OPTIONS:Mintrospection}
PLIST.introspection=	yes
MESON_ARGS+= -Dintrospection=enabled
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
BUILD_DEPENDS+= glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection
.else
TOOL_DEPENDS+= glib2-introspection-[0-9]*:../../devel/glib2-introspection
.endif

BUILDLINK_DEPMETHOD.gobject-introspection=	build
.  include "../../devel/gobject-introspection/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
# The native scanner canonicalizes sysroot paths; keep header lookup inside
# this consumer's declared buildlink tree.
_EMBERBSD_GI_REAL_SYSROOT!= cd ${CROSS_DESTDIR:Q} && pwd -P
BUILDLINK_TRANSFORM+= I:${_EMBERBSD_GI_REAL_SYSROOT}${PREFIX}:${BUILDLINK_DIR}

MESON_BINARIES+= g-ir-scanner g-ir-compiler
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
.endif
.else
MESON_ARGS+= -Dintrospection=disabled
.endif

.include "../../mk/bsd.prefs.mk"
