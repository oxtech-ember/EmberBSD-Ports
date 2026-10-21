# $NetBSD: Makefile,v 1.26 2026/09/06 09:34:38 markd Exp $

DISTNAME=	plasma-wayland-protocols-1.23.0
CATEGORIES=	devel kde
MASTER_SITES=	${MASTER_SITE_KDE:=plasma-wayland-protocols/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/kde/plasma-wayland-protocols
COMMENT=	Plasma Specific Protocols for Wayland
LICENSE=	gnu-lgpl-v2.1

USE_LANGUAGES=	c c++

.include "../../devel/cmake/build.mk"

BUILDLINK_API_DEPENDS.extra-cmake-modules+=	extra-cmake-modules>=5.60.0
.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# KDEInstallDirs6 always queries qtpaths for QT_INSTALL_PREFIX. A cross build
# finds the host qtpaths only through the target Qt6 configuration and
# QT_HOST_PATH. The package installs no Qt files, so Qt is a build dependency.
BUILDLINK_DEPMETHOD.qt6-qtbase?=	build
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif
.include "../../mk/bsd.pkg.mk"
