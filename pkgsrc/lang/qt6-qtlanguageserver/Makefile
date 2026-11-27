# $NetBSD: Makefile,v 1.31 2026/09/02 19:03:13 wiz Exp $

DISTNAME=	qtlanguageserver-everywhere-src-${QTVERSION}
PKGNAME=	qt6-qtlanguageserver-${QTVERSION}
COMMENT=	Qt6 language server implementation
CATEGORIES=	lang devel
LICENSE=	gnu-lgpl-v3 OR gnu-gpl-v2 OR gnu-gpl-v3

.include "../../x11/qt6-qtbase/Makefile.common"

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "aarch64"
PKGREVISION=	1
.endif

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	1	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"
