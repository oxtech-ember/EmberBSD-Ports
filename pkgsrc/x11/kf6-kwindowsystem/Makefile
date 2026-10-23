# $NetBSD: Makefile,v 1.18 2026/09/06 10:05:21 markd Exp $

DISTNAME=	kwindowsystem-${KF6VER}
PKGREVISION=	1
CATEGORIES=	x11

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Access to the windowing system
LICENSE=	gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/kf6.mk"

USE_TOOLS+=	pkg-config

# CMake validates pkg-config IMPORTED_TARGET paths before compiler wrappers run.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CONFIGURE_ENV+= PKG_CONFIG_SYSROOT_DIR=${CROSS_DESTDIR:Q}
.endif

PKGCONFIG_OVERRIDE+=		_KDE_build/KF6WindowSystem.pc
PKGCONFIG_OVERRIDE_STAGE=	post-build


.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/qt6-qttools/linguist.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
