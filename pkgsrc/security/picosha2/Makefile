# $NetBSD$

DISTNAME=	picosha2-1.0.1
CATEGORIES=	security
MASTER_SITES=	${MASTER_SITE_GITHUB:=okdshin/}
GITHUB_PROJECT=	PicoSHA2
GITHUB_TAG=	v${PKGVERSION_NOREV}
WRKSRC=		${WRKDIR}/PicoSHA2-${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/okdshin/PicoSHA2
COMMENT=	Header-only SHA-256 implementation in C++
LICENSE=	mit

NO_CONFIGURE=	yes
NO_BUILD=	yes
USE_LANGUAGES=	# none

INSTALLATION_DIRS+=	include share/licenses/picosha2
do-install:
	${INSTALL_DATA} ${WRKSRC}/picosha2.h ${DESTDIR}${PREFIX}/include/picosha2.h
	${INSTALL_DATA} ${WRKSRC}/LICENSE \
		${DESTDIR}${PREFIX}/share/licenses/picosha2/LICENSE

.include "../../mk/bsd.pkg.mk"
