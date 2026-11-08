# $NetBSD: Makefile,v 1.16 2026/09/02 19:02:58 wiz Exp $

.include "Makefile.common"

PKGNAME=		zint-${ZINT_VERSION}
PKGREVISION=		5
COMMENT=		Open source barcode generator and frontends
LICENSE=		gnu-gpl-v3 AND modified-bsd AND apache-2.0 AND mit AND isc AND imagemagick-license

BUILDLINK_DEPMETHOD.zint-lib=	full
.include "../../graphics/zint-lib/buildlink3.mk"

CMAKE_CONFIGURE_ARGS+=	-DMAN_INSTALL_DIR=${PREFIX}/${PKGMANDIR}
CMAKE_CONFIGURE_ARGS+=	-DZINT_USE_EXTERNAL_LIBRARY=ON

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
.include "../../mk/bsd.pkg.mk"
