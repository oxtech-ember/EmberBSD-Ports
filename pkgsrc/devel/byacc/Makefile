# $NetBSD: Makefile,v 1.35 2024/07/05 20:55:55 cheusov Exp $
#
# Origin: EmberBSD (AI-assisted); current shared upstream byacc recipe.

DISTNAME=	byacc-20260126
CATEGORIES=	devel
MASTER_SITES=	https://invisible-mirror.net/archives/byacc/
EXTRACT_SUFX=	.tgz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://invisible-island.net/byacc/byacc.html
COMMENT=	Berkeley Yacc
LICENSE=	public-domain

GNU_CONFIGURE=	YES

CONFIGURE_ARGS+=	--with-manpage-format=normal

MAKE_FILE=	makefile
TEST_TARGET=	check

.include "../../mk/bsd.pkg.mk"
