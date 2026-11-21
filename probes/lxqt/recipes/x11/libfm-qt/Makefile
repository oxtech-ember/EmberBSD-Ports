# $NetBSD: Makefile,v 1.66 2026/11/15 02:15:12 gutteridge Exp $

.include "../../meta-pkgs/lxqt/Makefile.common"

DISTNAME=	libfm-qt-2.5.0
CATEGORIES=	x11

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/lxqt/libfm-qt/
COMMENT=	Core library of PCManFM-Qt
LICENSE=	gnu-lgpl-v2.1 AND modified-bsd

USE_TOOLS+=	pkg-config perl

PKG_SYSCONFSUBDIR=	xdg

SUBST_CLASSES+=		prefix
SUBST_MESSAGE.prefix=	Fixing paths.
SUBST_STAGE.prefix=	pre-configure
SUBST_FILES.prefix=	src/core/fileinfo.cpp
SUBST_FILES.prefix+=	src/core/vfs/vfs-menu.c
SUBST_SED.prefix=	-e 's,/etc/xdg,${PKG_SYSCONFDIR},g'
SUBST_SED.prefix+=	-e 's,/usr/share,${PREFIX}/share,g'

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../meta-pkgs/lxqt/host-tools.mk"
.else
TOOL_DEPENDS+=	lxqt-build-tools>=2.5.0:../../devel/lxqt-build-tools
TOOL_DEPENDS+=	qt6-qttools-[0-9]*:../../devel/qt6-qttools
.endif

.include "../../devel/cmake/build.mk"

.include "../../graphics/libexif/buildlink3.mk"
.include "../../sysutils/lxqt-menu-data/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../x11/xcb-util-cursor/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
