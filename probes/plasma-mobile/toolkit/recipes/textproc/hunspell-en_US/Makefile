# $NetBSD: Makefile,v 1.5 2026/06/13 14:39:46 wiz Exp $
#

VERSION=	20260225
DISTNAME=	hunspell-en_US-2026.02.25
PKGNAME=	hunspell-en_US-${VERSION}
CATEGORIES=	textproc
MASTER_SITES=	https://github.com/en-wl/wordlist/releases/download/rel-2026.02.25/
EXTRACT_SUFX=	.zip

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://wordlist.aspell.net/dicts/
COMMENT=	US American English dictionaries for hunspell


WRKSRC=		${WRKDIR}
USE_LANGUAGES=	# none

INSTALLATION_DIRS=	share/hunspell share/doc/hunspell-en_US

do-build:

do-install:
	${INSTALL_DATA} ${WRKSRC}/en_US.aff ${WRKSRC}/en_US.dic ${DESTDIR}${PREFIX}/share/hunspell
	${INSTALL_DATA} ${WRKSRC}/README_en_US.txt \
		${DESTDIR}${PREFIX}/share/doc/hunspell-en_US

.include "../../mk/bsd.pkg.mk"
