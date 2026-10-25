# $NetBSD: Makefile,v 1.161 2026/09/02 19:02:04 wiz Exp $

.include "Makefile.common"

PKGREVISION=	2

COMMENT=	OpenType text shaping engine

MESON_ARGS+=	-Ddocs=disabled
# Use external icu support.
MESON_ARGS+=	-Dicu=disabled
MESON_ARGS+=	-Dtests=enabled

.include "../../mk/bsd.pkg.mk"
