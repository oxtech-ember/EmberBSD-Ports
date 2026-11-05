# $NetBSD$
# Origin: Mapbox gzip-hpp 0.1.0 with the KiCad 10.0.8 bounded decompressor API.
DISTNAME=	gzip-hpp-0.1.0
CATEGORIES=	archivers
MASTER_SITES=	${MASTER_SITE_GITHUB:=mapbox/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/mapbox/gzip-hpp
COMMENT=	Header-only C++ gzip and zlib compression library
LICENSE=	2-clause-bsd

NO_BUILD=	yes
DEPENDS+=	zlib>=1.3.2:../../devel/zlib
INSTALLATION_DIRS+=	include/gzip lib/cmake/gzip-hpp share/licenses/gzip-hpp

do-install:
	${INSTALL_DATA} ${WRKSRC}/include/gzip/*.hpp ${DESTDIR}${PREFIX}/include/gzip
	${INSTALL_DATA} ${FILESDIR}/gzip-hppConfig.cmake ${DESTDIR}${PREFIX}/lib/cmake/gzip-hpp/gzip-hppConfig.cmake
	${INSTALL_DATA} ${WRKSRC}/LICENSE.md ${DESTDIR}${PREFIX}/share/licenses/gzip-hpp/LICENSE.md

.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
