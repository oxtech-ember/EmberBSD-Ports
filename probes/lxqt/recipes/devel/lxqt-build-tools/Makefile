# $NetBSD: Makefile,v 1.59 2026/11/15 02:01:28 gutteridge Exp $

.include "../../meta-pkgs/lxqt/Makefile.common"

DISTNAME=	lxqt-build-tools-2.5.0
PKGREVISION=	2
CATEGORIES=	devel

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/lxqt/lxqt-build-tools/
COMMENT=	LXQt build tools
LICENSE=	modified-bsd

USE_TOOLS+=	pkg-config perl:run

# The installed translation script and CMake modules use Qt Linguist.
DEPENDS+=	qt6-qttools>=6.6:../../devel/qt6-qttools

PKG_SYSCONFSUBDIR=	xdg
CMAKE_CONFIGURE_ARGS+=	-DLXQT_ETC_XDG_DIR=${PKG_SYSCONFDIR}

BUILDLINK_DEPMETHOD.qt6-qtbase=	build
BUILDLINK_API_DEPENDS.qt6-qtbase+=	qt6-qtbase>=6.10.0
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
