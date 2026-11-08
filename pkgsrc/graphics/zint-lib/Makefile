# Shared libzint provider. The CLI and Qt frontends remain in graphics/zint.

.include "../zint/Makefile.common"

PKGNAME=		zint-lib-${ZINT_VERSION}
PKGREVISION=		${ZINT_LIB_REVISION}
COMMENT=		Zint barcode encoding library
LICENSE=		modified-bsd AND apache-2.0 AND mit AND isc AND imagemagick-license
# Older frontends own the library files now provided by this package.
CONFLICTS+=		zint<2.16.0nb5

CMAKE_CONFIGURE_ARGS+=	-DZINT_FRONTEND=OFF
CMAKE_CONFIGURE_ARGS+=	-DZINT_USE_QT=OFF
CMAKE_CONFIGURE_ARGS+=	-DZINT_SHARED=ON
CMAKE_CONFIGURE_ARGS+=	-DZINT_STATIC=OFF
CMAKE_CONFIGURE_ARGS+=	-DZINT_USE_PNG=ON

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/zint-lib
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/zint-lib/LICENSE
	${INSTALL_DATA} ${PKGSRCDIR}/licenses/apache-2.0 ${DESTDIR}${PREFIX}/share/licenses/zint-lib/LICENSE_apache-2.0
	${INSTALL_DATA} ${PKGSRCDIR}/licenses/imagemagick-license ${DESTDIR}${PREFIX}/share/licenses/zint-lib/LICENSE_imagemagick
	${INSTALL_DATA} ${FILESDIR}/NOTICE ${DESTDIR}${PREFIX}/share/licenses/zint-lib/NOTICE

.include "../../devel/cmake/build.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
