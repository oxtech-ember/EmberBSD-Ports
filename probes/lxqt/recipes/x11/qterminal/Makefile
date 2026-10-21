# $NetBSD: Makefile,v 1.52 2026/09/02 19:05:31 wiz Exp $

PKGREVISION= 4
.include "../../meta-pkgs/lxqt/Makefile.common"

DISTNAME=	qterminal-2.4.0
CATEGORIES=	x11

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/lxqt/qterminal/
COMMENT=	Terminal emulator for Qt6
LICENSE=	gnu-gpl-v2

USE_TOOLS+=	pkg-config perl

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../meta-pkgs/lxqt/host-tools.mk"
CMAKE_CONFIGURE_ARGS+=	-DQt6LinguistTools_DIR=${EMBERBSD_QT_HOST_PATH}/lib/cmake/Qt6LinguistTools
.else
TOOL_DEPENDS+=	lxqt-build-tools>=2.4.0:../../devel/lxqt-build-tools
TOOL_DEPENDS+=	qt6-qttools-[0-9]*:../../devel/qt6-qttools
.endif

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../x11/qtermwidget/buildlink3.mk"
.include "../../x11/plasma6-layer-shell-qt/buildlink3.mk"
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
