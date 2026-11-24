# $NetBSD$

PKG_OPTIONS_VAR=	PKG_OPTIONS.kvantum
PKG_SUPPORTED_OPTIONS=	kf6
PKG_SUGGESTED_OPTIONS=	kf6

.include "../../mk/bsd.options.mk"

# kf6: KWindowSystem gives blur behind translucent windows and menus.
# Without it the style is the same for themes that do not use blur.
.if !empty(PKG_OPTIONS:Mkf6)
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.else
CMAKE_CONFIGURE_ARGS+=	-DWITHOUT_KF=ON
.endif
