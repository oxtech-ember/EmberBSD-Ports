# $NetBSD: Makefile,v 1.55 2026/11/15 02:30:45 gutteridge Exp $

.include "../../meta-pkgs/lxqt/Makefile.common"

DISTNAME=	lxqt-runner-2.5.0
CATEGORIES=	x11

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/lxqt/lxqt-runner/
COMMENT=	Launch applications quickly by typing commands
LICENSE=	gnu-lgpl-v2.1

USE_TOOLS+=	pkg-config perl

AUTOSTART_CONF=		share/examples/autostart
PKG_SYSCONFSUBDIR=	xdg
MAKE_DIRS=		${PKG_SYSCONFDIR}/autostart

CONF_FILES+=	${AUTOSTART_CONF}/lxqt-runner.desktop \
		${PKG_SYSCONFDIR}/autostart/lxqt-runner.desktop

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../meta-pkgs/lxqt/host-tools.mk"
.else
TOOL_DEPENDS+=	lxqt-build-tools>=2.5.0:../../devel/lxqt-build-tools
TOOL_DEPENDS+=	qt6-qttools-[0-9]*:../../devel/qt6-qttools
.endif

BUILDLINK_API_DEPENDS.lxqt-globalkeys+=	lxqt-globalkeys>=2.5.0
.include "../../x11/lxqt-globalkeys/buildlink3.mk"
BUILDLINK_API_DEPENDS.muparser+= muparser>=2.3.6
.include "../../math/muparser/buildlink3.mk"
.include "../../x11/plasma6-layer-shell-qt/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
