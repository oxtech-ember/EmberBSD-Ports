# $NetBSD: Makefile,v 1.13 2026/09/02 19:04:20 wiz Exp $

DISTNAME=	polkit-qt-1-0.201.1
PKGNAME=	${DISTNAME:S/-qt-1-/-qt6-/}
PKGREVISION=	1
CATEGORIES=	security
MASTER_SITES=	https://download.kde.org/stable/polkit-qt-1/
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://invent.kde.org/libraries/polkit-qt-1
COMMENT=	Qt6 Wrapper around PolicyKit
LICENSE=	gnu-lgpl-v2.1


USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config

CMAKE_CONFIGURE_ARGS+=	-DQT_MAJOR_VERSION=6

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# CMake validates imported pkg-config paths on the build host.
CONFIGURE_ENV+= PKG_CONFIG_SYSROOT_DIR=${CROSS_DESTDIR}
.endif

PKGCONFIG_OVERRIDE+=	polkit-qt6-1.pc.cmake polkit-qt6-agent-1.pc.cmake
PKGCONFIG_OVERRIDE+=	polkit-qt6-core-1.pc.cmake polkit-qt6-gui-1.pc.cmake

.include "../../devel/cmake/build.mk"
.include "../../security/polkit/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
