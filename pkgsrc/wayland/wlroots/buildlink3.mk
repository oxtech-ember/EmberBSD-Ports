# $NetBSD: buildlink3.mk,v 1.2 2026/07/20 17:27:15 kikadf Exp $

BUILDLINK_TREE+=	wlroots

.if !defined(WLROOTS_BUILDLINK3_MK)
WLROOTS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.wlroots+=	wlroots>=0.20.2nb4
BUILDLINK_PKGSRCDIR.wlroots?=	../../wayland/wlroots

pkgbase := wlroots
.include "../../mk/pkg-build-options.mk"

.include "../../devel/wayland/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
PREFER.MesaLib= pkgsrc
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../x11/libdrm/buildlink3.mk"
BUILDLINK_API_DEPENDS.libxkbcommon+= libxkbcommon>=1.13.2nb1
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/pixman/buildlink3.mk"
.if !empty(PKG_BUILD_OPTIONS.wlroots:Mlibinput)
.include "../../devel/libopeninput/buildlink3.mk"
.endif
.if !empty(PKG_BUILD_OPTIONS.wlroots:Msession)
UDEV_REQUIRED= yes
.include "../../sysutils/seatd/buildlink3.mk"
.include "../../mk/udev.buildlink3.mk"
.endif
.if !empty(PKG_BUILD_OPTIONS.wlroots:Mdrm)
.include "../../x11/libdisplay-info/buildlink3.mk"
.endif
.if !empty(PKG_BUILD_OPTIONS.wlroots:Mcolor-management)
.include "../../graphics/lcms2/buildlink3.mk"
.endif
.if !empty(PKG_BUILD_OPTIONS.wlroots:Mlibliftoff)
.include "../../graphics/libliftoff/buildlink3.mk"
.endif
.if !empty(PKG_BUILD_OPTIONS.wlroots:Mvulkan)
.include "../../graphics/vulkan-loader/buildlink3.mk"
.endif
.if !empty(PKG_BUILD_OPTIONS.wlroots:Mx11)
.include "../../x11/xcb-util-renderutil/buildlink3.mk"
.endif
.if !empty(PKG_BUILD_OPTIONS.wlroots:Mxwayland)
.include "../../wayland/xwayland/buildlink3.mk"
.include "../../x11/xcb-util-wm/buildlink3.mk"
.endif
.if !empty(PKG_BUILD_OPTIONS.wlroots:Mxcb-errors)
.include "../../x11/xcb-util-errors/buildlink3.mk"
.endif

.endif # WLROOTS_BUILDLINK3_MK

BUILDLINK_TREE+= -wlroots
