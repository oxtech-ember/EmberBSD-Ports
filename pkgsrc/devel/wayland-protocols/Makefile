# $NetBSD: Makefile,v 1.25 2026/06/07 18:26:20 wiz Exp $

DISTNAME=	wayland-protocols-1.49
CATEGORIES=	devel
MASTER_SITES=	https://gitlab.freedesktop.org/wayland/wayland-protocols/-/releases/${PKGVERSION_NOREV}/downloads/
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://wayland.freedesktop.org/
COMMENT=	Additional wayland functionality
LICENSE=	mit

USE_TOOLS+=		pkg-config

MESON_ARGS+=		-Dtests=false

PKGCONFIG_OVERRIDE+=	wayland-protocols.pc.in

.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:tl} == "yes"
# Explicit host tools include native pkg-config metadata for enum headers.
.if defined(EMBERBSD_WAYLAND_SCANNER)
.include "cross-scanner.mk"
.else
TOOL_DEPENDS+=				wayland>=1.26.0nb1:../../devel/wayland
MESON_BINARIES+=			wayland_scanner
MESON_BINARY_KEY.wayland_scanner=	${PREFIX}/bin/wayland-scanner
MESON_BINARY.wayland_scanner=		${TOOLBASE}/bin/wayland-scanner
.endif
.endif

.include "../../devel/meson/build.mk"
BUILDLINK_API_DEPENDS.wayland+= wayland>=1.26.0nb1
.include "../../devel/wayland/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
