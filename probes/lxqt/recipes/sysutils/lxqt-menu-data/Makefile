# $NetBSD: Makefile,v 1.22 2026/09/02 19:04:32 wiz Exp $

PKGREVISION= 3
.include "../../meta-pkgs/lxqt/Makefile.common"

DISTNAME=	lxqt-menu-data-2.4.0
CATEGORIES=	sysutils x11

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/lxqt/lxqt-menu-data/
COMMENT=	freedesktop.org compliant menu files for LXQt
LICENSE=	gnu-lgpl-v2.1

USE_TOOLS+=	pkg-config perl
# This package generates translated menu data. It has no compiled source.
USE_LANGUAGES=
USE_CXX_FEATURES=

MENU_CONF=		share/examples/menus
PKG_SYSCONFSUBDIR=	xdg
MAKE_DIRS=		${PKG_SYSCONFDIR}/menus

CONF_FILES=	${MENU_CONF}/lxqt-applications.menu \
		${PKG_SYSCONFDIR}/menus/lxqt-applications.menu
CONF_FILES+=	${MENU_CONF}/lxqt-applications-compact.menu \
		${PKG_SYSCONFDIR}/menus/lxqt-applications-compact.menu
CONF_FILES+=	${MENU_CONF}/lxqt-applications-fm.menu \
		${PKG_SYSCONFDIR}/menus/lxqt-applications-fm.menu
CONF_FILES+=	${MENU_CONF}/lxqt-config.menu \
		${PKG_SYSCONFDIR}/menus/lxqt-config.menu
CONF_FILES+=	${MENU_CONF}/lxqt-panel-applications.menu \
		${PKG_SYSCONFDIR}/menus/lxqt-panel-applications.menu

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../meta-pkgs/lxqt/host-tools.mk"
CMAKE_CONFIGURE_ARGS+= -DQt6_DIR=${EMBERBSD_QT_HOST_PATH}/lib/cmake/Qt6
.else
TOOL_DEPENDS+=	lxqt-build-tools>=2.4.0:../../devel/lxqt-build-tools
TOOL_DEPENDS+=	qt6-qttools-[0-9]*:../../devel/qt6-qttools
.endif

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
