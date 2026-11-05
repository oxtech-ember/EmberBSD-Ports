# $NetBSD$

DISTNAME=	MicroTeX-61aaa7cc354de91d5898ffb0b2a6c62628d9a76f
PKGNAME=	microtex-0.0.20260814
CATEGORIES=	graphics
MASTER_SITES=	-https://codeload.github.com/desktop-app/MicroTeX/tar.gz/61aaa7cc354de91d5898ffb0b2a6c62628d9a76f
HOMEPAGE=	https://github.com/desktop-app/MicroTeX
COMMENT=	Qt-backed mathematical typesetting library
LICENSE=	mit AND ofl-v1.1 AND knuth-fonts AND dsrom-fonts

USE_LANGUAGES=	c c++
USE_CXX_FEATURES+=	c++20
CMAKE_CONFIGURE_ARGS+=	-DQT=ON -DBUILD_EXAMPLE=OFF
CMAKE_CONFIGURE_ARGS+=	-DQT_VERSION_MAJOR=6 -DHAVE_LOG=OFF -DGRAPHICS_DEBUG=OFF

.include "../../devel/cmake/build.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
