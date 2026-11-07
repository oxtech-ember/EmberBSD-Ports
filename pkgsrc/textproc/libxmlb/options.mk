# $NetBSD: options.mk,v 1.2 2026/02/19 16:56:26 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.libxmlb
PKG_SUPPORTED_OPTIONS+=	doc
PKG_SUGGESTED_OPTIONS=

.include "../../mk/bsd.options.mk"

PLIST_VARS+=		doc gir

PRINT_PLIST_AWK+=	{ if (/^share\/gtk-doc/) $$0 = "$${PLIST.doc}" $$0 }
.if !empty(PKG_OPTIONS:Mdoc)
TOOL_DEPENDS+=		gtk-doc-[0-9]*:../../textproc/gtk-doc
PLIST.doc=		yes
.else
MESON_ARGS+=		-Dgtkdoc=false
.endif

# The sysroot g-ir-scanner uses the target Python and cannot run on the build host.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
MESON_ARGS+=		-Dintrospection=false
.else
PLIST.gir=		yes
.endif
