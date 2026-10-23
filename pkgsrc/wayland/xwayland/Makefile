# $NetBSD: Makefile,v 1.5 2026/07/08 07:41:45 wiz Exp $

DISTNAME=	xwayland-24.1.14
PKGREVISION=	3
CATEGORIES=	wayland
MASTER_SITES=	${MASTER_SITE_XORG:=xserver/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://xorg.freedesktop.org/
COMMENT=	Server for running X clients under Wayland from modular X.org
LICENSE=	mit AND modified-bsd AND x11 # with no-advertising clause

# Origin: EmberBSD (AI-assisted). Keep the complete upstream test targets.
USE_TOOLS+=	pkg-config
DEPENDS+=	xkeyboard-config>=2.48:../../x11/xkeyboard-config
BUILDLINK_API_DEPENDS.xkbcomp+=	xkbcomp>=1.5.0
BUILDLINK_API_DEPENDS.libei+=	libei>=1.6.0nb1

# Require the accelerated paths instead of accepting an auto-disabled DRI3.
MESON_ARGS+=	-Dglamor=true -Dglx=true -Ddri3=true -Dxvfb=true
# These paths belong to the target, not the pkg-config build sysroot.
MESON_ARGS+=	-Dxkb_dir=${PREFIX}/share/X11/xkb
MESON_ARGS+=	-Dxkb_bin_dir=${PREFIX}/bin
MESON_ARGS+=	-Dxkb_output_dir=${VARBASE}/db/xkb

.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if !defined(EMBERBSD_WAYLAND_SCANNER)
PKG_FAIL_REASON+= "Xwayland requires the common native Wayland scanner"
.else
.include "../../devel/wayland-protocols/cross-scanner.mk"
.endif
.endif

.if ${OPSYS} == "NetBSD"
# Shared root-owned socket directories must survive clear_tmp at boot.
RCD_SCRIPTS+=	x11_runtime
MESON_ARGS+=	-Dsecure-rpc=false
.  if ${OPSYS_VERSION} < 100000
CPPFLAGS+=	-D_OPENBSD_SOURCE # reallocarray
.  endif
.endif

.include "../../devel/wayland/platform.mk"

.if empty(PLATFORM_SUPPORTS_WAYLAND:M[Yy][Ee][Ss])
PKG_SKIP_REASON+=	"Platform does not support Wayland"
.endif

post-install:
	${RM} ${DESTDIR}${PREFIX}/lib/xorg/protocol.txt
	${RM} ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/Xserver.1
	if [ -f ${DESTDIR}${PREFIX}/share/doc/xorg-server/Xserver-DTrace.xml ]; then \
		${RM} ${DESTDIR}${PREFIX}/share/doc/xorg-server/Xserver-DTrace.xml; \
	fi

.include "../../devel/input-headers/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../x11/xorgproto/buildlink3.mk"
.include "../../graphics/libepoxy/buildlink3.mk"
.if ${X11_TYPE} == "modular"
.include "../../x11/libXfont2/buildlink3.mk"
.else
.include "../../graphics/freetype2/buildlink3.mk"
.endif
.include "../../x11/libxcvt/buildlink3.mk"
.include "../../x11/libdrm/buildlink3.mk"
.include "../../x11/libei/buildlink3.mk"
.include "../../x11/xkbcomp/buildlink3.mk"
.include "../../x11/libxkbfile/buildlink3.mk"
.include "../../x11/libxshmfence/buildlink3.mk"
.include "../../x11/pixman/buildlink3.mk"
.include "../../x11/xtrans/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
