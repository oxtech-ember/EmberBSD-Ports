# $NetBSD: Makefile,v 1.18 2025/11/17 11:00:58 wiz Exp $

DISTNAME=	potrace-1.16
PKGREVISION=	1
CATEGORIES=	graphics
MASTER_SITES=	http://potrace.sourceforge.net/download/
MASTER_SITES+=	${MASTER_SITE_SOURCEFORGE:=potrace/}

MAINTAINER=	adam@NetBSD.org
HOMEPAGE=	https://potrace.sourceforge.net/
COMMENT=	Utility for transforming bitmaps into vector graphics
LICENSE=	gnu-gpl-v2

USE_LIBTOOL=		yes
GNU_CONFIGURE=		yes
CONFIGURE_ARGS+=	--with-libpotrace
TEST_TARGET=		check

# Upstream shares these static inline helpers with library frontends.
INSTALLATION_DIRS+=	include/potrace

post-install:
	${INSTALL_DATA} ${WRKSRC}/src/bitmap.h ${DESTDIR}${PREFIX}/include/potrace/bitmap.h

.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
