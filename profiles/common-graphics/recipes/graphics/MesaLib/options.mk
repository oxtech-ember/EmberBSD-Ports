# $NetBSD: options.mk,v 1.86 2025/03/07 07:00:33 wiz Exp $
# Keep the common GL interfaces. PowerVR is an explicit Vulkan option.
PKG_OPTIONS_VAR= PKG_OPTIONS.MesaLib
PKG_SUPPORTED_OPTIONS= llvm x11 wayland powervr
PKG_SUGGESTED_OPTIONS= llvm x11 wayland
.include "../../mk/bsd.options.mk"
.for option in llvm x11 wayland
.if empty(PKG_OPTIONS:M${option})
PKG_FAIL_REASON+= "The common graphics candidate requires the ${option} Mesa option"
.endif
.endfor

PLIST_VARS+= powervr
.if !empty(PKG_OPTIONS:Mpowervr)
PLIST.powervr= yes
.endif
