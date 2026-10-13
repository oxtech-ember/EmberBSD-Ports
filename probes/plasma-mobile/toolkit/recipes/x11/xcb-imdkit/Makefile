# $NetBSD: Makefile,v 1.5 2025/01/23 23:27:30 riastradh Exp $

DISTNAME=	xcb-imdkit-1.0.9
CATEGORIES=	x11
MASTER_SITES=	https://download.fcitx-im.org/fcitx5/xcb-imdkit/
EXTRACT_SUFX=	.tar.zst

MAINTAINER=	ryoon@NetBSD.org
HOMEPAGE=	https://github.com/fcitx/xcb-imdkit
COMMENT=	Implementation of xim protocol in xcb
LICENSE=	gnu-lgpl-v2.1

USE_TOOLS+=	pkg-config
USE_LANGUAGES+=	c c++

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_EXPORT_COMPILE_COMMANDS=ON
CMAKE_CONFIGURE_ARGS+=	-DUSE_SYSTEM_UTHASH=ON
TEST_TARGET=		test

PKGCONFIG_OVERRIDE+=	src/xcb-imdkit.pc.in

BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,--as-needed

.include "../../devel/cmake/build.mk"
.include "../../devel/extra-cmake-modules/buildlink3.mk"
BUILDLINK_API_DEPENDS.uthash+=	uthash>=2.4.0
.include "../../devel/uthash/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.include "../../x11/xcb-util/buildlink3.mk"
.include "../../x11/xcb-util-keysyms/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
