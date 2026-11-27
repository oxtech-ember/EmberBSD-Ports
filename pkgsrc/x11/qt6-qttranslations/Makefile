# $NetBSD: Makefile,v 1.15 2026/09/02 19:05:31 wiz Exp $

DISTNAME=	qttranslations-everywhere-src-${QTVERSION}
PKGNAME=	qt6-qttranslations-${QTVERSION}
PKGREVISION=	1
CATEGORIES=	x11
COMMENT=	Qt6 translations
LICENSE=	modified-bsd AND gnu-gpl-v3

QT_TARGET_METADATA_MODE= translations

.include "../../x11/qt6-qtbase/Makefile.common"

.include "../../devel/qt6-qttools/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	2	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"
