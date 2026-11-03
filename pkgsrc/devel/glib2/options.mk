# $NetBSD: options.mk,v 1.24 2022/11/26 09:55:19 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.glib2
PKG_SUPPORTED_OPTIONS=	tests

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
PKG_SUPPORTED_OPTIONS+=	cocoa
.endif

.include "../../mk/bsd.options.mk"

PLIST_VARS+=	cocoa nococoa

# if this options is enabled, use quartz for gtk{2,3}
.if !empty(PKG_OPTIONS:Mcocoa)
MESON_ARGS+=	-Duse_cocoa=true
# Cocoa tests remain unsupported by the existing upstream guard.
.if !empty(PKG_OPTIONS:Mtests)
PKG_FAIL_REASON+= "GLib tests are unavailable with cocoa"
.endif
PLIST.cocoa=	yes
.else
PLIST.nococoa=	yes
.endif

# Build upstream test executables only in the explicit test graph.
.if !empty(PKG_OPTIONS:Mtests) && empty(PKG_OPTIONS:Mcocoa)
MESON_ARGS+= -Dtests=true
.else
MESON_ARGS+= -Dtests=false
.endif
