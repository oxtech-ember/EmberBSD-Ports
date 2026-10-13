# $NetBSD: Makefile,v 1.122 2026/06/22 19:09:42 wiz Exp $
# Origin: pkgsrc devel/automake; EmberBSD current release update.

DISTNAME=	automake-1.19
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GNU:=automake/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.gnu.org/software/automake/automake.html
COMMENT=	GNU Standards-compliant Makefile generator
LICENSE=	gnu-gpl-v2

AUTOCONF_REQD+=	2.73
USE_TOOLS+=	autoconf gm4:run perl:run

PLIST_SUBST+=		PKG_DIR_VERSION=1.19
GNU_CONFIGURE=		yes
INFO_FILES=		yes
TEST_TARGET=		check

.include "../../mk/bsd.pkg.mk"
