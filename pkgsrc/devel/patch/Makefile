# $NetBSD: Makefile,v 1.47 2025/04/21 16:32:26 wiz Exp $
# Origin: pkgsrc devel/patch, updated to GNU patch 2.8 (2025-03-29).
# The upstream release includes the former pkgsrc security patches.

DISTNAME=	patch-2.8
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GNU:=patch/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.gnu.org/software/patch/patch.html
COMMENT=	Patch files using diff output
LICENSE=	gnu-gpl-v3

GNU_CONFIGURE=	yes
USE_TOOLS+=	awk

.include "../../mk/bsd.prefs.mk"

CONFIGURE_ARGS+=	--program-prefix=g

INSTALLATION_DIRS=	${PKGGNUDIR}bin ${PKGGNUDIR}${PKGMANDIR}/man1

post-install:
	${LN} -sf ${PREFIX}/bin/gpatch ${DESTDIR}${PREFIX}/${PKGGNUDIR}bin/patch
	${LN} -sf ${PREFIX}/${PKGMANDIR}/man1/gpatch.1 ${DESTDIR}${PREFIX}/${PKGGNUDIR}${PKGMANDIR}/man1/patch.1

.include "../../mk/bsd.pkg.mk"
