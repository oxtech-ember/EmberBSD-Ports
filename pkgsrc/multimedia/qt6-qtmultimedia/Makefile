# $NetBSD: Makefile,v 1.46 2026/09/02 19:03:49 wiz Exp $

DISTNAME=	qtmultimedia-everywhere-src-${QTVERSION}
PKGNAME=	qt6-qtmultimedia-${QTVERSION}
PKGREVISION=	3
COMMENT=	Qt6 module with multimedia
CATEGORIES=	multimedia
LICENSE=	gnu-lgpl-v3 OR gnu-gpl-v2 OR gnu-gpl-v3

# ALSA is experimental
CONFIGURE_ARGS+=	-no-alsa

.include "options.mk"

.include "../../x11/qt6-qtbase/Makefile.common"

PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Multimedia.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6MultimediaWidgets.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6SpatialAudio.pc

.include "../../graphics/qt6-qtshadertools/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.if ${OPSYS} == "NetBSD" && (${MACHINE_ARCH} == "aarch64" || ${MACHINE_ARCH} == "x86_64") && !empty(PKG_OPTIONS:Mgstreamer)
.  if ${MACHINE_ARCH} == "aarch64"
PKGREVISION=	5
.  else
PKGREVISION=	4
.  endif
.endif

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	5	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"
