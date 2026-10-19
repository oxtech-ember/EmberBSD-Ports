# $NetBSD: Makefile,v 1.4 2026/09/02 19:04:50 wiz Exp $

PKGREVISION= 4
.include "../../meta-pkgs/lxqt/Makefile.common"

DISTNAME=	lxqt-wayland-session-0.4.1
CATEGORIES=	wayland

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/lxqt/lxqt-wayland-session/
COMMENT=	Files needed for the LXQt Wayland Session
LICENSE=	gnu-lgpl-v2.1 AND gnu-lgpl-v2 AND gnu-lgpl-v3 AND \
		mit AND modified-bsd AND cc-by-sa-v4.0

USE_TOOLS+=	pkg-config perl

SUBST_CLASSES+=		path
SUBST_STAGE.path=	pre-configure
SUBST_MESSAGE.path=	Fix path
SUBST_FILES.path=	CMakeLists.txt
SUBST_VARS.path+=	PKG_SYSCONFDIR

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../meta-pkgs/lxqt/host-tools.mk"
# This finder only validates the target command path. It does not execute it.
CMAKE_CONFIGURE_ARGS+=	-DXdgUserDirsUpdate_EXECUTABLE:FILEPATH=${PREFIX}/bin/xdg-user-dirs-update
pre-configure:
	${TEST} -x ${CROSS_DESTDIR}${PREFIX}/bin/xdg-user-dirs-update
.else
TOOL_DEPENDS+=	lxqt-build-tools>=2.4.0:../../devel/lxqt-build-tools
TOOL_DEPENDS+=	qt6-qttools-[0-9]*:../../devel/qt6-qttools
.endif
DEPENDS+=	qtxdg-tools>=4.0.0:../../x11/qtxdg-tools
DEPENDS+=	xdg-user-dirs-[0-9]*:../../x11/xdg-user-dirs
DEPENDS+=	lxqt-session-[0-9]*:../../x11/lxqt-session
DEPENDS+=	qt6-qttools>=6.12.0:../../devel/qt6-qttools

.include "../../x11/plasma6-layer-shell-qt/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../sysutils/seatd/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
