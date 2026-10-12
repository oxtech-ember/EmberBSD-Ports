# $NetBSD: options.mk,v 1.24 2026/05/15 17:00:56 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.pango
PKG_SUPPORTED_OPTIONS=	introspection libthai x11
PKG_SUGGESTED_OPTIONS=	x11

PKG_SUGGESTED_OPTIONS+=	introspection

.include "../../mk/bsd.options.mk"

PLIST_VARS+=	introspection
PLIST_VARS+=	x11

###
### X11 support
###
.if !empty(PKG_OPTIONS:Mx11)
# fix for pangox.pc
PLIST.x11=	yes
MESON_ARGS+=	-Dxft=enabled
BUILDLINK_API_DEPENDS.Xft2+=	Xft2>=2.1.7nb3
.include "../../x11/libXft/buildlink3.mk"
.include "../../x11/libXrender/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
BUILDLINK_DEPMETHOD.libXt?=	build # only for configure
.include "../../x11/libXt/buildlink3.mk"
.else
MESON_ARGS+=	-Dxft=disabled
.endif

###
### gobject-introspection
###
.if !empty(PKG_OPTIONS:Mintrospection)
PLIST.introspection=	yes
MESON_ARGS+=	-Dintrospection=enabled
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
BUILD_DEPENDS+= glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
# The native scanner reads metadata for the target ABI.
MAKE_ENV+= XDG_DATA_DIRS=${CROSS_DESTDIR:Q}${PREFIX:Q}/share
_EMBERBSD_GI_REAL_SYSROOT!= cd ${CROSS_DESTDIR:Q} && pwd -P
BUILDLINK_TRANSFORM+= I:${_EMBERBSD_GI_REAL_SYSROOT}${PREFIX}:${BUILDLINK_DIR}
MESON_BINARIES+= g-ir-scanner g-ir-compiler
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
.else
TOOL_DEPENDS+= glib2-introspection-[0-9]*:../../devel/glib2-introspection
.endif
BUILDLINK_DEPMETHOD.gobject-introspection=	build
BUILDLINK_API_DEPENDS.gobject-introspection+=	gobject-introspection>=1.84.0
.include "../../devel/gobject-introspection/buildlink3.mk"
.else
MESON_ARGS+=	-Dintrospection=disabled
.endif

###
### Thai language support
###
.if !empty(PKG_OPTIONS:Mlibthai)
MESON_ARGS+=	-Dlibthai=enabled
.include "../../devel/libthai/buildlink3.mk"
.else
MESON_ARGS+=	-Dlibthai=disabled
.endif

.include "../../mk/bsd.prefs.mk"
