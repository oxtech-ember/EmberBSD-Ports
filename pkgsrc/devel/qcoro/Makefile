# $NetBSD: Makefile,v 1.5 2026/09/02 19:01:43 wiz Exp $

DISTNAME=	qcoro-0.13.0
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=qcoro/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/qcoro/qcoro
COMMENT=	C++ Coroutines for Qt
LICENSE=	mit

.include "../../devel/cmake/build.mk"

USE_LANGUAGES=		c c++
USE_CXX_FEATURES+=	c++20

CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
# Keep the common QtDBus API on hosts where upstream disables it by default.
CMAKE_CONFIGURE_ARGS+=	-DQCORO_WITH_QTDBUS=ON
# Examples are not installed or part of the package's public interface.
CMAKE_CONFIGURE_ARGS+=	-DQCORO_BUILD_EXAMPLES=OFF
PKG_OPTIONS_VAR=	PKG_OPTIONS.qcoro
PKG_SUPPORTED_OPTIONS=	tests
.include "../../mk/bsd.options.mk"
.if !empty(PKG_OPTIONS:Mtests)
CMAKE_CONFIGURE_ARGS+=	-DQCORO_BUILD_TESTING=ON
TEST_DEPENDS+=	dbus-[0-9]*:../../sysutils/dbus
TEST_TARGET=	test
.else
CMAKE_CONFIGURE_ARGS+=	-DQCORO_BUILD_TESTING=OFF
.endif

.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../net/qt6-qtwebsockets/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
