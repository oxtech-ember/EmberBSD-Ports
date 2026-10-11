# $NetBSD: Makefile,v 1.17 2026/09/06 10:05:18 markd Exp $

DISTNAME=	kcodecs-${KF6VER}
CATEGORIES=	textproc

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Collection of methods to manipulate strings using various encodings
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/kf6.mk"

TOOL_DEPENDS+=	gperf-[0-9]*:../../devel/gperf

.include "../../devel/qt6-qttools/linguist.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
