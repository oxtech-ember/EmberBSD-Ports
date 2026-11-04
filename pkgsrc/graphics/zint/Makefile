# $NetBSD: Makefile,v 1.16 2026/09/02 19:02:58 wiz Exp $

DISTNAME=	zint-2.16.0-src
PKGNAME=	${DISTNAME:S/-src//}
PKGREVISION=	4
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_SOURCEFORGE:=zint/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.zint.org.uk/
COMMENT=	Open source barcode generating solution
LICENSE=	gnu-gpl-v3 AND modified-bsd AND apache-2.0 AND mit AND isc AND imagemagick-license

USE_LANGUAGES=	c c++

CMAKE_CONFIGURE_ARGS+=	-DMAN_INSTALL_DIR=${PREFIX}/${PKGMANDIR}

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/zint
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/zint/LICENSE
	${INSTALL_DATA} ${WRKSRC}/frontend/COPYING ${DESTDIR}${PREFIX}/share/licenses/zint/COPYING.GPL
	${INSTALL_DATA} ${WRKSRC}/frontend_qt/res/LICENSE_lucide ${DESTDIR}${PREFIX}/share/licenses/zint/LICENSE_lucide
	${INSTALL_DATA} ${WRKSRC}/frontend_qt/res/LICENSE_feathericons ${DESTDIR}${PREFIX}/share/licenses/zint/LICENSE_feathericons
	${INSTALL_DATA} ${PKGSRCDIR}/licenses/apache-2.0 ${DESTDIR}${PREFIX}/share/licenses/zint/LICENSE_apache-2.0
	${INSTALL_DATA} ${PKGSRCDIR}/licenses/imagemagick-license ${DESTDIR}${PREFIX}/share/licenses/zint/LICENSE_imagemagick
	${INSTALL_DATA} ${FILESDIR}/NOTICE ${DESTDIR}${PREFIX}/share/licenses/zint/NOTICE

.include "options.mk"
.include "../../devel/cmake/build.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
