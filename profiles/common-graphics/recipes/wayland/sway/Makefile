# $NetBSD: Makefile,v 1.4 2026/09/02 19:04:51 wiz Exp $

DISTNAME=	sway-1.12
PKGREVISION=	3
CATEGORIES=	wayland
MASTER_SITES=	${MASTER_SITE_GITHUB:=swaywm/}

MAINTAINER=	kikadf@NetBSD.org
HOMEPAGE=	https://swaywm.org/
COMMENT=	Tilling, i3-compatible Wayland compositor
LICENSE=	mit

USE_TOOLS+=	pkg-config

# Origin: pkgsrc, adapted by EmberBSD (AI-assisted).
# Require each selected desktop feature and use native source generators.
MESON_ARGS+=	--wrap-mode=nofallback
MESON_ARGS+=	-Dman-pages=enabled -Dtray=enabled -Dsd-bus-provider=basu
MESON_ARGS+=	-Dgdk-pixbuf=enabled

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if defined(EMBERBSD_WAYLAND_SCANNER)
.include "../../devel/wayland-protocols/cross-scanner.mk"
.else
PKG_FAIL_REASON+= "Cross Sway requires the validated native Wayland scanner"
.endif
MESON_BINARIES+=	scdoc
MESON_BINARY.scdoc=	${TOOLBASE}/bin/scdoc
.endif

EGDIR=		${PREFIX}/share/examples/sway
OWN_DIRS+=	${PKG_SYSCONFDIR}/sway
CONF_FILES=	${EGDIR}/config ${PKG_SYSCONFDIR}/sway/config


post-install:
	${INSTALL_SCRIPT} ${FILESDIR}/startsway.sh \
		${DESTDIR}${PREFIX}/bin/startsway

.include "../../devel/meson/build.mk"
.include "../../textproc/scdoc/tool.mk"
.include "../../devel/basu/buildlink3.mk"
.include "../../devel/libevdev-chunk/buildlink3.mk"
.include "../../devel/pango/buildlink3.mk"
.include "../../devel/pcre2/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../graphics/cairo/buildlink3.mk"
.include "../../graphics/gdk-pixbuf2/buildlink3.mk"
.include "../../sysutils/seatd/buildlink3.mk"
.include "../../textproc/json-c/buildlink3.mk"
.include "../../wayland/wlroots/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
