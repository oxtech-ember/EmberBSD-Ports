# $NetBSD: Makefile,v 1.5 2026/09/02 19:04:51 wiz Exp $

DISTNAME=		wlroots-0.20.2
PKGREVISION=		4
CATEGORIES=		wayland
MASTER_SITE_GITLAB=	https://gitlab.freedesktop.org/
MASTER_SITES=		${MASTER_SITE_GITLAB:=wlroots/}
GITLAB_TAG=		${PKGVERSION_NOREV}

MAINTAINER=		kikadf@NetBSD.org
HOMEPAGE=		https://gitlab.freedesktop.org/wlroots/wlroots
COMMENT=		Wayland compositor library
LICENSE=		mit

USE_TOOLS+=		pkg-config

# Origin: pkgsrc, adapted by EmberBSD (AI-assisted) for explicit feature closure.
MESON_ARGS+=		-Dallocators=gbm --wrap-mode=nofallback

SUBST_CLASSES+=		path
SUBST_STAGE.path=	pre-configure
SUBST_MESSAGE.path=	Fixing pathes
SUBST_FILES.path+=	xcursor/xcursor.c
SUBST_VARS.path+=	PREFIX X11BASE

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "NetBSD" && ${OPSYS_VERSION} < 110000
PKG_FAIL_REASON+=	"DRM_IOCTL_GET_UNIQUE is not allowed on render nodes"
.endif

BUILDLINK_TRANSFORM+=	rm:-Wl,--fatal-warnings

.include "options.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if defined(EMBERBSD_WAYLAND_SCANNER)
.include "../../devel/wayland-protocols/cross-scanner.mk"
.else
PKG_FAIL_REASON+= "Cross wlroots requires the validated native Wayland scanner metadata"
.endif
.endif

.if !empty(PKG_OPTIONS:Mdrm)
EMBERBSD_NATIVE_GRAPHICS_PC= hwdata:0.412
.include "../../sysutils/hwdata/native-meson.mk"
.endif

.include "../../devel/meson/build.mk"
# Core keyboard types use input codes even without the libinput backend.
BUILDLINK_DEPMETHOD.input-headers= build
.include "../../devel/input-headers/buildlink3.mk"
BUILDLINK_API_DEPENDS.wayland+= wayland>=1.26.0nb1
.include "../../devel/wayland/buildlink3.mk"
BUILDLINK_API_DEPENDS.wayland-protocols+= wayland-protocols>=1.49
.include "../../devel/wayland-protocols/buildlink3.mk"
PREFER.MesaLib= pkgsrc
BUILDLINK_API_DEPENDS.MesaLib+= MesaLib>=26.2.4nb2
.include "../../graphics/MesaLib/buildlink3.mk"
BUILDLINK_API_DEPENDS.libdrm+= libdrm>=2.4.134nb1
.include "../../x11/libdrm/buildlink3.mk"
BUILDLINK_API_DEPENDS.libxkbcommon+= libxkbcommon>=1.13.2nb1
.include "../../x11/libxkbcommon/buildlink3.mk"
BUILDLINK_API_DEPENDS.pixman+= pixman>=0.46.4
.include "../../x11/pixman/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
