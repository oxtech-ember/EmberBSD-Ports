# $NetBSD$

PKG_OPTIONS_VAR=	PKG_OPTIONS.ibus
PKG_SUPPORTED_OPTIONS=	gtk2 gtk3 gtk4 introspection xim
PKG_SUGGESTED_OPTIONS=	gtk2 gtk3 introspection xim
.include "../../mk/bsd.options.mk"

PLIST_VARS+=	gtk2 gtk3 gtk4 introspection setup xim gtk3wayland
.for option in gtk2 gtk3 gtk4 introspection xim
.  if !empty(PKG_OPTIONS:M${option})
CONFIGURE_ARGS+=	--enable-${option}=yes
PLIST.${option}=	yes
.  else
CONFIGURE_ARGS+=	--disable-${option}
.  endif
.endfor

.if !empty(PKG_OPTIONS:Mgtk2)
GTK2_IMMODULES=	yes
.include "../../x11/gtk2/modules.mk"
.include "../../x11/gtk2/buildlink3.mk"
.endif
.if !empty(PKG_OPTIONS:Mgtk3)
GTK3_IMMODULES=	yes
BUILDLINK_API_DEPENDS.gtk3+=	gtk3+>=3.12.0
.include "../../x11/gtk3/modules.mk"
.include "../../x11/gtk3/buildlink3.mk"
.else
CONFIGURE_ARGS+=	--disable-ui
.endif
.if !empty(PKG_OPTIONS:Mgtk4)
BUILDLINK_API_DEPENDS.gtk4+=	gtk4>=4.14.0
.include "../../x11/gtk4/buildlink3.mk"
.endif
.if !empty(PKG_OPTIONS:Mxim) && empty(PKG_OPTIONS:Mgtk2) && empty(PKG_OPTIONS:Mgtk3)
PKG_FAIL_REASON+=	"The IBus XIM server requires GTK 2 or GTK 3."
.endif
.if !empty(PKG_OPTIONS:Mintrospection)
TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection
BUILDLINK_API_DEPENDS.gobject-introspection+=	gobject-introspection>=0.9.6
BUILDLINK_DEPMETHOD.gobject-introspection=	build
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/gobject-introspection/autotools.mk"
.  if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The query runner requires the linked target ELF. Libtool normally creates a
# shell launcher for the temporary scanner program in an uninstalled tree.
# Vala supplies the make rules that turn the generated GIRs into VAPI files.
MAKE_FLAGS+= VAPIGEN_MAKEFILE=${TOOLBASE:Q}/share/vala/Makefile.vapigen
MAKE_FLAGS+= _gir_libtool=--no-libtool
MAKE_FLAGS+= IBus_1_0_gir_LIBS=ibus-1.0
MAKE_FLAGS+= IBus_1_0_gir_LDFLAGS=-L${WRKSRC:Q}/src/.libs
# Wayland input-method types live in a private convenience archive. Include
# that archive in the type dumper while recording the public IBus SONAME.
IBUS_WAYLAND_GIR_FLAGS= -L${WRKSRC}/src/.libs
IBUS_WAYLAND_GIR_FLAGS+= --extra-library=${WRKSRC}/client/wayland/.libs/libibuswaylandim.a
IBUS_WAYLAND_GIR_FLAGS+= --pkg=wayland-client --pkg=xkbcommon --extra-library=m
MAKE_FLAGS+= IBusWaylandIM_1_0_gir_LIBS=ibus-1.0
MAKE_FLAGS+= IBusWaylandIM_1_0_gir_LDFLAGS=${IBUS_WAYLAND_GIR_FLAGS:Q}
# The private IMModule namespace describes one function and has no GTypes.
MAKE_FLAGS+= IBusIMModule_1_0_gir_LDFLAGS=--header-only
# The emoji dialog's GType implementation is linked into the GTK panel.
IBUS_EMOJI_GIR_FLAGS= -L${WRKSRC}/src/.libs
IBUS_EMOJI_GIR_FLAGS+= --extra-library=${WRKSRC}/bindings/vala/.libs/libibus-emoji-dialog-1.0.a
IBUS_EMOJI_GIR_FLAGS+= --pkg=gthread-2.0 --pkg=x11 --pkg=xi --extra-library=m
MAKE_FLAGS+= IBusEmojiDialog_1_0_gir_LIBS=ibus-1.0
MAKE_FLAGS+= IBusEmojiDialog_1_0_gir_LDFLAGS=${IBUS_EMOJI_GIR_FLAGS:Q}
# The distribution GIR files were generated for the release host.
post-extract:
	${RUN} ${RM} -f ${WRKSRC}/src/IBus-1.0.gir \
	    ${WRKSRC}/client/wayland/IBusWaylandIM-1.0.gir \
	    ${WRKSRC}/tools/IBusIMModule-1.0.gir \
	    ${WRKSRC}/bindings/vala/IBusEmojiDialog-1.0.gir
.  endif
.else
# Vala clients can use the interface shipped in the same upstream release.
INSTALLATION_DIRS+=	share/vala/vapi
post-install:
	${INSTALL_DATA} ${WRKSRC}/bindings/vala/ibus-1.0.vapi \
	    ${WRKSRC}/bindings/vala/ibus-1.0.deps ${DESTDIR}${PREFIX}/share/vala/vapi
.endif
.if !empty(PKG_OPTIONS:Mgtk3) && !empty(PKG_OPTIONS:Mintrospection)
PLIST.setup=	yes
DEPENDS+=	${PYPKGPREFIX}-gobject3-[0-9]*:../../devel/py-gobject3
.  if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
SUBST_CLASSES+=		ibus-python
SUBST_STAGE.ibus-python=	post-build
SUBST_FILES.ibus-python=	setup/ibus-setup
SUBST_SED.ibus-python=	-e 's,${TOOL_PYTHONBIN},${PYTHONBIN},g'
.  endif
.else
CONFIGURE_ARGS+=	--disable-setup
.endif
