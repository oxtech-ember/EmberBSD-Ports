# $NetBSD$
# Origin: EmberBSD contributors; common Parson provider at upstream commit.
DISTNAME=	parson-1.5.4.20260915
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=kgabis/}
GITHUB_TAG=	ec53fb6528b45811df9db0db22cab96a94a96a11
WRKSRC=		${WRKDIR}/parson-${GITHUB_TAG}
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/kgabis/parson/
COMMENT=	Lightweight JSON library written in C
LICENSE=	mit
USE_LANGUAGES=	c
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
INSTALLATION_DIRS+=	share/doc/parson
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/doc/parson/LICENSE
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
