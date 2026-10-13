# $NetBSD: Makefile,v 1.30 2026/09/02 19:03:03 wiz Exp $

DISTNAME=	fcitx5-qt-5.1.16
CATEGORIES=	inputmethod
MASTER_SITES=	https://download.fcitx-im.org/fcitx5/fcitx5-qt/
EXTRACT_SUFX=	.tar.zst

MAINTAINER=	ryoon@NetBSD.org
HOMEPAGE=	https://download.fcitx-im.org/fcitx5/fcitx5-qt/
COMMENT=	Qt library and IM module for fcitx5
LICENSE=	gnu-lgpl-v2.1

USE_PKGLOCALEDIR=	yes
USE_LANGUAGES=		c c++

CMAKE_CONFIGURE_ARGS+= -DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+= -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
USE_TOOLS+=		pkg-config

CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT4=off
CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT5=OFF
CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT6=ON
CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT6_WAYLAND_WORKAROUND=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_QT6PLUGINDIR=${PREFIX}/qt6/plugins

.include "../../devel/cmake/build.mk"

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../inputmethod/fcitx5/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/qt6-qtwayland/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../devel/gettext-tools/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
