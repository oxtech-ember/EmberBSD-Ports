# $NetBSD$

PKG_OPTIONS_VAR=	PKG_OPTIONS.libadwaita
PKG_SUPPORTED_OPTIONS=	examples introspection
PKG_SUGGESTED_OPTIONS=	examples introspection

.include "../../mk/bsd.options.mk"

PLIST_VARS+=	examples introspection
.if !empty(PKG_OPTIONS:Mexamples)
PLIST.examples=	yes
MESON_ARGS+=	-Dexamples=true
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.else
MESON_ARGS+=	-Dexamples=false
.endif

.if !empty(PKG_OPTIONS:Mintrospection)
PLIST.introspection=	yes
MESON_ARGS+=	-Dintrospection=enabled -Dvapi=true
TOOL_DEPENDS+=	vala-[0-9]*:../../lang/vala
TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
BUILD_DEPENDS+=	glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MAKE_ENV+= XDG_DATA_DIRS=${CROSS_DESTDIR:Q}${PREFIX:Q}/share
_EMBERBSD_GI_REAL_SYSROOT!= cd ${CROSS_DESTDIR:Q} && pwd -P
BUILDLINK_TRANSFORM+= I:${_EMBERBSD_GI_REAL_SYSROOT}${PREFIX}:${BUILDLINK_DIR}
MESON_BINARIES+= g-ir-scanner g-ir-compiler
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
# Cross: the GIR introspect binary links with the target sysroot paths.
LDFLAGS+=	-L${CROSS_DESTDIR:Q}${PREFIX:Q}/lib
BUILDLINK_DEPMETHOD.gobject-introspection=	build
BUILDLINK_API_DEPENDS.gobject-introspection+=	gobject-introspection>=1.86.0nb11
.endif
.include "../../devel/gobject-introspection/buildlink3.mk"
.else
MESON_ARGS+=	-Dintrospection=disabled -Dvapi=false
.endif
