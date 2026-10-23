# $NetBSD: Makefile,v 1.3 2024/06/07 19:57:36 ryoon Exp $

DISTNAME=	notofonts.github.io-noto-monthly-release-2026.10.01
PKGNAME=	noto-fonts-20261001
CATEGORIES=	fonts
MASTER_SITES=	${MASTER_SITE_GITHUB:=notofonts/}
GITHUB_PROJECT=	notofonts.github.io
GITHUB_TAG=	noto-monthly-release-2026.10.01

MAINTAINER=	ryoon@NetBSD.org
HOMEPAGE=	https://notofonts.github.io/
COMMENT=	Google Noto fonts, except CJK and Emoji
LICENSE=	ofl-v1.1

CONFLICTS+=	noto-ttf-[0-9]*

USE_LANGUAGES=	# none
NO_CONFIGURE=	yes
NO_BUILD=	yes

FONTDIR=	${PREFIX}/share/fonts/X11/TTF
FONTS_DIRS.ttf=	${FONTDIR}

INSTALLATION_DIRS=	share/fonts/X11/TTF share/licenses/noto-fonts

do-install:
	set -e; for fontdir in ${WRKSRC}/fonts/*/hinted/ttf; do \
		[ ! -d "$$fontdir" ] || ${INSTALL_DATA} "$$fontdir"/*.ttf ${DESTDIR}${FONTDIR}; \
	done
	${INSTALL_DATA} ${WRKSRC}/fonts/LICENSE ${DESTDIR}${PREFIX}/share/licenses/noto-fonts/OFL.txt

# Do not install all ttf/otf font files.
#.include "../../mk/fonts.mk"
.include "../../mk/bsd.pkg.mk"
