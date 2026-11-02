# $NetBSD: Makefile,v 1.7 2026/09/02 19:02:07 wiz Exp $

DISTNAME=	ccleste-1.4.0
PKGREVISION=	6
CATEGORIES=	games
MASTER_SITES=	${MASTER_SITE_GITHUB:=lemon32767/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/lemon32767/ccleste
COMMENT=	Portable version of the Celeste Classic 2D platform game
#LICENSE=	# freeware

USE_TOOLS+=	gmake pax pkg-config

# Origin: EmberBSD (AI-assisted). EmberBSD keeps SDL3 only: build the SDL3
# and SDL3_mixer port (files/sdl30compat.inc.c) instead of SDL2 or SDL 1.2.
MAKE_FLAGS+=	SDL_VER=3

INSTALLATION_DIRS+=	bin
INSTALLATION_DIRS+=	libexec
INSTALLATION_DIRS+=	share/applications
INSTALLATION_DIRS+=	share/ccleste/data
INSTALLATION_DIRS+=	share/pixmaps

post-extract:
	${CP} ${FILESDIR}/sdl30compat.inc.c ${WRKSRC}/

pre-configure:
	${SED} -e "s,@PREFIX@,${PREFIX},g" ${FILESDIR}/ccleste.sh > \
		${WRKDIR}/ccleste.sh

do-install:
	${INSTALL_SCRIPT} ${WRKDIR}/ccleste.sh \
		${DESTDIR}${PREFIX}/bin/ccleste
	${INSTALL_PROGRAM} ${WRKSRC}/ccleste \
		${DESTDIR}${PREFIX}/libexec/ccleste
	${INSTALL_DATA} ${FILESDIR}/ccleste.desktop \
		${DESTDIR}${PREFIX}/share/applications/ccleste.desktop
	${INSTALL_DATA} ${WRKSRC}/icon.png \
		${DESTDIR}${PREFIX}/share/pixmaps/ccleste.png
	cd ${WRKSRC}/data && ${PAX} -rw -pp . \
		${DESTDIR}${PREFIX}/share/ccleste/data

.include "../../audio/SDL3_mixer/buildlink3.mk"
.include "../../devel/SDL3/buildlink3.mk"
.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../mk/bsd.pkg.mk"
