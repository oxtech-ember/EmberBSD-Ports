# $NetBSD: Makefile,v 1.9 2026/09/06 10:23:29 markd Exp $

DISTNAME=	aurorae-${PLASMAVER}
CATEGORIES=	graphics

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Themeable window decoration for KWin
LICENSE=	gnu-gpl-v2 AND mit

.include "../../meta-pkgs/kde/plasma6.mk"

USE_TOOLS+=	msgmerge pkg-config

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# This launcher uses POSIX shell syntax and runs on the target.
REPLACE_INTERPRETER+= target-sh
REPLACE.target-sh.old= /usr/bin/bash
REPLACE.target-sh.new= /bin/sh
REPLACE_FILES.target-sh= plasma-apply-aurorae.cmake
.else
REPLACE_SH+= plasma-apply-aurorae.cmake
.endif

.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kcolorscheme/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kpackage/buildlink3.mk"
.include "../../devel/qt6-qttools/buildlink3.mk"
.include "../../graphics/kf6-ksvg/buildlink3.mk"
.include "../../net/kf6-knewstuff/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/plasma6-kdecoration/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
