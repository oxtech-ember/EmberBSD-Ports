# $NetBSD: Makefile,v 1.161 2026/09/02 19:02:04 wiz Exp $

.include "Makefile.common"

.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION=	1
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

COMMENT=	OpenType text shaping engine

MESON_ARGS+=	-Ddocs=disabled
MESON_ARGS+=	-Dpng=enabled
# Use external icu support.
MESON_ARGS+=	-Dicu=disabled

.include "../../graphics/png/buildlink3.mk"
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	1	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"
