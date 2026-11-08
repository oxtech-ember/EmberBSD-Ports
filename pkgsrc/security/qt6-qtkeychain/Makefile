# $NetBSD$

DISTNAME=	qtkeychain-0.16.0
PKGNAME=	qt6-${DISTNAME}
CATEGORIES=	security
MASTER_SITES=	${MASTER_SITE_GITHUB:=frankosterfeld/}
GITHUB_PROJECT=	qtkeychain

HOMEPAGE=	https://github.com/frankosterfeld/qtkeychain/
COMMENT=	Platform-independent Qt API for storing passwords securely
LICENSE=	2-clause-bsd

USE_LANGUAGES=		c c++
USE_TOOLS+=		pkg-config

CMAKE_CONFIGURE_ARGS+=	-DBUILD_WITH_QT6:BOOL=ON
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TEST_APPLICATION:BOOL=OFF

.include "../../devel/cmake/build.mk"

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../devel/qt6-qttools/buildlink3.mk"
.include "../../security/libsecret/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
