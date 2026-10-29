# $NetBSD$
# Origin: EmberBSD (AI-assisted); common libspng provider.
DISTNAME= libspng-0.7.4
CATEGORIES= graphics
MASTER_SITES= ${MASTER_SITE_GITHUB:=randy408/}
GITHUB_TAG= v${PKGVERSION_NOREV}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://libspng.org/
COMMENT= PNG decoding and encoding library
LICENSE= 2-clause-bsd AND libpng-2.0
USE_LANGUAGES= c
CMAKE_CONFIGURE_ARGS+= -DCMAKE_BUILD_TYPE=Release
PKGCONFIG_OVERRIDE+= cmake/libspng.pc.in
.include "../../devel/cmake/build.mk"
.include "../../devel/zlib/buildlink3.mk"
post-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/licenses/libspng
	${INSTALL_DATA} ${WRKSRC:Q}/LICENSE ${DESTDIR:Q}${PREFIX:Q}/share/licenses/libspng/BSD-2-Clause
	${INSTALL_DATA} ${FILESDIR:Q}/libpng-2.0 ${DESTDIR:Q}${PREFIX:Q}/share/licenses/libspng/libpng-2.0

.include "../../mk/bsd.pkg.mk"
