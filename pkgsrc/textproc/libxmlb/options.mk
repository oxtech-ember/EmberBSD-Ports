# $NetBSD: options.mk,v 1.2 2026/02/19 16:56:26 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.libxmlb
PKG_SUPPORTED_OPTIONS+=	doc tests
PKG_SUGGESTED_OPTIONS=

.include "../../mk/bsd.options.mk"

PLIST_VARS+=		doc gir tests

PRINT_PLIST_AWK+=	{ if (/^share\/gtk-doc/) $$0 = "$${PLIST.doc}" $$0 }
.if !empty(PKG_OPTIONS:Mdoc)
TOOL_DEPENDS+=		gtk-doc-[0-9]*:../../textproc/gtk-doc
PLIST.doc=		yes
.else
MESON_ARGS+=		-Dgtkdoc=false
.endif

PRINT_PLIST_AWK+=	{ if (/^(libexec|share)\/installed-tests\//) $$0 = "$${PLIST.tests}" $$0 }
.if !empty(PKG_OPTIONS:Mtests)
MESON_ARGS+=		-Dtests=true
PLIST.tests=		yes
.else
MESON_ARGS+=		-Dtests=false
.endif

# The sysroot g-ir-scanner uses the target Python and cannot run on the build host.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
MESON_ARGS+=		-Dintrospection=false
.else
PLIST.gir=		yes
.endif
