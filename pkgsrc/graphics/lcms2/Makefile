# $NetBSD: Makefile,v 1.26 2026/05/12 16:09:35 gdt Exp $

DISTNAME=	lcms2-2.19.1
PKGREVISION=	2
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_SOURCEFORGE:=lcms/}

MAINTAINER=	gdt@NetBSD.org
HOMEPAGE=	http://www.littlecms.com/
COMMENT=	Little Color Management System - a color management library
LICENSE=	mit AND modified-bsd

# Upstream added cmake support in 2.19, but that has not been declared
# official/favored.  Pending upstream commentary (requested 20260430)
# or some compelling reason, the package will remain on autoconf,
# because the of the usual pattern of cmake build systems having
# regressions from autoconf in various areas, typically cross
# compilation and testing non-installed versions, at least until those
# are assessed.
USE_LIBTOOL=		yes
GNU_CONFIGURE=		yes
PKGCONFIG_OVERRIDE=	lcms2.pc.in
TEST_TARGET=		check
INSTALLATION_DIRS+=	share/licenses/lcms2

post-install:
	${INSTALL_DATA} ${FILESDIR:Q}/PDFium-BSD-3-Clause ${DESTDIR:Q}${PREFIX:Q}/share/licenses/lcms2/PDFium-BSD-3-Clause

# Don't switch to cmake yet as upstream has no declared it to be the
# official build system.
#.include "../../devel/cmake/build.mk"

# libtool can link tificc directly to libtiff's dependencies.
.include "../../archivers/xz/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../graphics/jbigkit/buildlink3.mk"
.include "../../graphics/lerc/buildlink3.mk"

.include "../../graphics/tiff/buildlink3.mk"
.include "../../mk/jpeg.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
