# $NetBSD$

DISTNAME=	rang-3.3
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=agauniyal/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/agauniyal/rang/
COMMENT=	Header-only terminal styling library for C++
LICENSE=	unlicense

NO_CONFIGURE=	yes
NO_BUILD=	yes
USE_LANGUAGES=	# none

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/include
	${INSTALL_DATA} ${WRKSRC}/include/rang.hpp ${DESTDIR}${PREFIX}/include/rang.hpp
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/rang
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/rang/LICENSE

.include "../../mk/bsd.pkg.mk"
