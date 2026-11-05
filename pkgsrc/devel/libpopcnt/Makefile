# $NetBSD$

DISTNAME=	libpopcnt-4.2
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=kimwalisch/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/kimwalisch/libpopcnt
COMMENT=	Fast population count header-only library
LICENSE=	2-clause-bsd

NO_BUILD=	yes

INSTALLATION_DIRS+=	include share/licenses/libpopcnt lib/cmake/LibPopcnt
do-install:
	${INSTALL_DATA} ${WRKSRC}/libpopcnt.h ${DESTDIR}${PREFIX}/include/libpopcnt.h
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/libpopcnt/LICENSE
	${INSTALL_DATA} ${FILESDIR}/LibPopcntConfig.cmake ${DESTDIR}${PREFIX}/lib/cmake/LibPopcnt/LibPopcntConfig.cmake

.include "../../mk/bsd.pkg.mk"
