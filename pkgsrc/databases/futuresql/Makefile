# $NetBSD$

DISTNAME=	futuresql-0.1.1
CATEGORIES=	databases
MASTER_SITES=	https://download.kde.org/stable/futuresql/
EXTRACT_SUFX=	.tar.xz

HOMEPAGE=	https://invent.kde.org/libraries/futuresql
COMMENT=	Non-blocking database library for Qt
LICENSE=	2-clause-bsd

.include "../../devel/cmake/build.mk"

USE_LANGUAGES=	c++
USE_CXX_FEATURES+=	c++20

CMAKE_CONFIGURE_ARGS+=	-DQT_MAJOR_VERSION=6
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_EXAMPLES=OFF

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
