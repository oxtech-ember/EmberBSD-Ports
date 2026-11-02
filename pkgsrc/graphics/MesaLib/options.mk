# $NetBSD: options.mk,v 1.86 2025/03/07 07:00:33 wiz Exp $
# Keep the common GL interfaces. Drivers are not package options.
PKG_OPTIONS_VAR= PKG_OPTIONS.MesaLib
# The upstream test suite is opt-in; it adds a build-only GoogleTest dependency.
PKG_SUPPORTED_OPTIONS= llvm x11 wayland tests
PKG_SUGGESTED_OPTIONS= llvm x11 wayland
.include "../../mk/bsd.options.mk"
.for option in llvm x11 wayland
.if empty(PKG_OPTIONS:M${option})
PKG_FAIL_REASON+= "The common graphics candidate requires the ${option} Mesa option"
.endif
.endfor
