# $NetBSD: options.mk,v 1.21 2026/05/15 17:00:57 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.harfbuzz
PKG_SUPPORTED_OPTIONS+=	introspection
PKG_SUGGESTED_OPTIONS=

PKG_SUGGESTED_OPTIONS+=	introspection

.include "../../mk/bsd.options.mk"

PLIST_VARS+=		introspection

PRINT_PLIST_AWK+=	{ if (/^bin\/hb-info/) $$0 = "$${PLIST.introspection}" $$0 }
PRINT_PLIST_AWK+=	{ if (/^bin\/hb-ot-shape-closure/) $$0 = "$${PLIST.introspection}" $$0 }
PRINT_PLIST_AWK+=	{ if (/^bin\/hb-shape/) $$0 = "$${PLIST.introspection}" $$0 }
PRINT_PLIST_AWK+=	{ if (/^bin\/hb-subset/) $$0 = "$${PLIST.introspection}" $$0 }
PRINT_PLIST_AWK+=	{ if (/^include\/harfbuzz\/hb-glib.h/) $$0 = "$${PLIST.introspection}" $$0 }
PRINT_PLIST_AWK+=	{ if (/^include\/harfbuzz\/hb-gobject/) $$0 = "$${PLIST.introspection}" $$0 }
PRINT_PLIST_AWK+=	{ if (/^lib\/girepository/) $$0 = "$${PLIST.introspection}" $$0 }
PRINT_PLIST_AWK+=	{ if (/^lib\/libharfbuzz-gobject/) $$0 = "$${PLIST.introspection}" $$0 }
PRINT_PLIST_AWK+=	{ if (/^lib\/pkgconfig\/harfbuzz-gobject.pc/) $$0 = "$${PLIST.introspection}" $$0 }
PRINT_PLIST_AWK+=	{ if (/^share\/gir-1.0/) $$0 = "$${PLIST.introspection}" $$0 }
.if !empty(PKG_OPTIONS:Mintrospection)
MESON_ARGS+=	-Dintrospection=enabled
.include "../../devel/glib2/buildlink3.mk"
# XXX This should be TOOL_DEPENDS, no?
BUILDLINK_DEPMETHOD.gobject-introspection+=	build
.include "../../devel/gobject-introspection/buildlink3.mk"
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
MESON_BINARY.g-ir-compiler= ${_EMBER_GI_COMPILER}
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
.else
TOOL_DEPENDS+= glib2-introspection-[0-9]*:../../devel/glib2-introspection
.endif
PLIST.introspection=	yes
.else
MESON_ARGS+=	-Dintrospection=disabled
.endif
