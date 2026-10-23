# $NetBSD: options.mk,v 1.4 2023/09/04 13:50:42 wiz Exp $
# Origin: EmberBSD (AI-assisted), optional GTK3 event-sound adapter.

PKG_OPTIONS_VAR=	PKG_OPTIONS.libcanberra
PKG_SUPPORTED_OPTIONS=	gtk3
# Qt consumers use the core Event Sound API. GTK applications opt in.
PKG_SUGGESTED_OPTIONS=

.include "../../mk/bsd.options.mk"

PLIST_VARS+=		gtk-any gtk gtk3

# Do not detect an unrelated GTK installation in the build environment.
CONFIGURE_ARGS+=	--disable-gtk
.if !empty(PKG_OPTIONS:Mgtk3)
CONFIGURE_ARGS+=	--enable-gtk3
PLIST.gtk-any=		yes
PLIST.gtk3=		yes
BUILDLINK_API_DEPENDS.gtk3+=	gtk3+>=3.24.52
.include "../../x11/gtk3/buildlink3.mk"
.else
CONFIGURE_ARGS+=	--disable-gtk3
.endif
