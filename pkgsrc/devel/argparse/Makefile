# $NetBSD$

DISTNAME=	argparse-3.2
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=p-ranav/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/p-ranav/argparse
COMMENT=	Single-header argument parser for C++17
LICENSE=	mit

USE_LANGUAGES=	c++
CMAKE_CONFIGURE_ARGS+=	-DARGPARSE_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DARGPARSE_BUILD_SAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DARGPARSE_INSTALL=ON

INSTALLATION_DIRS+=	share/licenses/argparse
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/argparse/LICENSE

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
