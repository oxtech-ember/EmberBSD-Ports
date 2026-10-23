# $NetBSD: options.mk,v 1.1 2026/04/13 17:20:09 kikadf Exp $
# Origin: pkgsrc, extended by EmberBSD (AI-assisted).
# Every selected feature is required; omitted features are explicitly disabled.
PKG_OPTIONS_VAR= PKG_OPTIONS.wlroots
PKG_SUPPORTED_OPTIONS= glesv2 vulkan drm libinput x11 session color-management libliftoff examples xwayland xcb-errors
PKG_SUGGESTED_OPTIONS= ${PKG_SUPPORTED_OPTIONS}

.include "../../mk/bsd.options.mk"

_WLR_RENDERERS=
_WLR_BACKENDS=
PLIST_VARS+= glesv2 vulkan drm libinput x11 session xwayland
.for option in glesv2 vulkan drm libinput x11 session xwayland
.if !empty(PKG_OPTIONS:M${option})
PLIST.${option}= yes
.endif
.endfor
.if !empty(PKG_OPTIONS:Mglesv2)
_WLR_RENDERERS+= gles2
.endif
.if !empty(PKG_OPTIONS:Mvulkan)
_WLR_RENDERERS+= vulkan
# Shader compilation is a host operation, not a target library dependency.
TOOL_DEPENDS+= glslang>=1.4.341.0:../../graphics/glslang
TOOLS_CREATE+= glslang
TOOLS_PATH.glslang= ${TOOLBASE}/bin/glslang
.include "../../graphics/vulkan-loader/buildlink3.mk"
.endif
.for backend in drm libinput x11
.if !empty(PKG_OPTIONS:M${backend})
_WLR_BACKENDS+= ${backend}
.endif
.endfor
MESON_ARGS+= -Drenderers=${_WLR_RENDERERS:ts,}
MESON_ARGS+= -Dbackends=${_WLR_BACKENDS:ts,}

.if (!empty(PKG_OPTIONS:Mdrm) || !empty(PKG_OPTIONS:Mlibinput)) && empty(PKG_OPTIONS:Msession)
PKG_FAIL_REASON+= "The wlroots drm and libinput backends require the session option"
.endif
.if !empty(PKG_OPTIONS:Mlibliftoff) && empty(PKG_OPTIONS:Mdrm)
PKG_FAIL_REASON+= "The wlroots libliftoff option requires the drm backend"
.endif
.if !empty(PKG_OPTIONS:Mxcb-errors) && empty(PKG_OPTIONS:Mxwayland)
PKG_FAIL_REASON+= "The wlroots xcb-errors option requires xwayland"
.endif
.for feature in session color-management libliftoff xwayland xcb-errors
.if !empty(PKG_OPTIONS:M${feature})
MESON_ARGS+= -D${feature}=enabled
.else
MESON_ARGS+= -D${feature}=disabled
.endif
.endfor
.if !empty(PKG_OPTIONS:Mexamples)
MESON_ARGS+= -Dexamples=true
.include "../../graphics/cairo/buildlink3.mk"
.else
MESON_ARGS+= -Dexamples=false
.endif
.if !empty(PKG_OPTIONS:Mdrm)
# Upstream resolves pnp.ids through native pkg-config metadata.
TOOL_DEPENDS+= hwdata>=0.412:../../sysutils/hwdata
.include "../../x11/libdisplay-info/buildlink3.mk"
.endif
.if !empty(PKG_OPTIONS:Mlibinput)
.include "../../devel/libopeninput/buildlink3.mk"
.endif
.if !empty(PKG_OPTIONS:Msession)
UDEV_REQUIRED= yes
.include "../../sysutils/seatd/buildlink3.mk"
.include "../../mk/udev.buildlink3.mk"
.endif
.if !empty(PKG_OPTIONS:Mcolor-management)
.include "../../graphics/lcms2/buildlink3.mk"
.endif
.if !empty(PKG_OPTIONS:Mlibliftoff)
.include "../../graphics/libliftoff/buildlink3.mk"
.endif
.if !empty(PKG_OPTIONS:Mx11)
.include "../../x11/xcb-util-renderutil/buildlink3.mk"
.endif
.if !empty(PKG_OPTIONS:Mxwayland)
.include "../../wayland/xwayland/buildlink3.mk"
.include "../../x11/xcb-util-wm/buildlink3.mk"
.endif
.if !empty(PKG_OPTIONS:Mxcb-errors)
.include "../../x11/xcb-util-errors/buildlink3.mk"
.endif
