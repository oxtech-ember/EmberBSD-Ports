# $NetBSD: options.mk,v 1.86 2025/03/07 07:00:33 wiz Exp $
# The default keeps the full common graphics set. Select software rendering with:
# PKG_OPTIONS.MesaLib+= softpipe-only -llvm -wayland
PKG_OPTIONS_VAR= PKG_OPTIONS.MesaLib
# The upstream test suite is opt-in; it adds a build-only GoogleTest dependency.
PKG_SUPPORTED_OPTIONS= llvm x11 wayland tests softpipe-only
PKG_SUGGESTED_OPTIONS= llvm x11 wayland
.include "../../mk/bsd.options.mk"
.if !empty(PKG_OPTIONS:Msoftpipe-only)
.if empty(PKG_OPTIONS:Mx11) || !empty(PKG_OPTIONS:Mllvm) || !empty(PKG_OPTIONS:Mwayland)
PKG_FAIL_REASON+= "softpipe-only requires x11 and excludes llvm and wayland"
.endif
.else
.for option in llvm x11 wayland
.if empty(PKG_OPTIONS:M${option})
PKG_FAIL_REASON+= "The common graphics candidate requires the ${option} Mesa option"
.endif
.endfor
.endif
