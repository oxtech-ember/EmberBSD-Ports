# $NetBSD: Makefile,v 1.14 2026/09/06 10:23:28 markd Exp $

PLASMAVER=	6.8.0

DISTNAME=	kwayland-${PLASMAVER}
CATEGORIES=	devel

HOMEPAGE=	https://invent.kde.org/plasma/kwayland
COMMENT=	Qt-style Client and Server library wrapper for the Wayland libraries
LICENSE=	gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/plasma6.mk"

# XML/CMake metadata belongs to the target dependency graph.
BUILDLINK_API_DEPENDS.plasma-wayland-protocols+= plasma-wayland-protocols>=1.23.0

USE_TOOLS+=	pkg-config

# Compile upstream tests with the current EmberBSD API; execution is separate.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=ON
CMAKE_CONFIGURE_ARGS+=	-DKF_IGNORE_PLATFORM_CHECK=true

.include "../../mk/bsd.prefs.mk"

# Wayland wire key/button codes are also required on BSD targets.
.if ${OPSYS} != "Linux"
BUILDLINK_DEPMETHOD.input-headers= build
.include "../../devel/input-headers/buildlink3.mk"
.endif

.include "../../devel/wayland/platform.mk"
.if empty(PLATFORM_SUPPORTS_WAYLAND:M[Yy][Ee][Ss])
PKG_SKIP_REASON+=       "Platform does not support Wayland"
.endif

.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
