# $NetBSD: options.mk,v 1.9 2026/05/02 12:41:52 pin Exp $

PKG_OPTIONS_VAR=		PKG_OPTIONS.lxqt
PKG_OPTIONS_OPTIONAL_GROUPS=	wm
PKG_OPTIONS_GROUP.wm=		openbox xfce4-wm wayland
PKG_SUGGESTED_OPTIONS=		wayland

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mopenbox)
DEPENDS+=	openbox>=3.6.1:../../wm/openbox
DEPENDS+=	obconf-qt>=0.16.6:../../wm/obconf-qt
.endif

.if !empty(PKG_OPTIONS:Mxfce4-wm)
DEPENDS+=	xfce4-wm>=4.14.6:../../wm/xfce4-wm
.endif

# The selected Wayland session retains a compositor, lock action and idle
# manager. An explicit X11 selection keeps its upstream dependencies.
.if !empty(PKG_OPTIONS:Mwayland)
DEPENDS+=	lxqt-session>=2.4.0nb6:../../x11/lxqt-session
DEPENDS+=	lxqt-wayland-session>=0.4.1:../../wayland/lxqt-wayland-session
DEPENDS+=	labwc>=0.20.2nb2:../../wayland/labwc
DEPENDS+=	swaylock>=1.8.6:../../wayland/swaylock
DEPENDS+=	swayidle>=1.9.0:../../wayland/swayidle
DEPENDS+=	qt6-qtwayland>=6.12.0:../../devel/qt6-qtwayland
.endif
