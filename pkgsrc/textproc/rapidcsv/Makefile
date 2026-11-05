# $NetBSD$

DISTNAME=	rapidcsv-9.07
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=d99kris/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/d99kris/rapidcsv
COMMENT=	Header-only CSV parser and writer for C++
LICENSE=	modified-bsd

USE_LANGUAGES=	c++
CMAKE_CONFIGURE_ARGS+=	-DRAPIDCSV_BUILD_TESTS:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib

INSTALLATION_DIRS+=	share/licenses/rapidcsv
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE \
		${DESTDIR}${PREFIX}/share/licenses/rapidcsv/LICENSE

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
