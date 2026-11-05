# $NetBSD$
# Origin: QCAD dxflib 3.26.4 official source, mirrored by Debian.
DISTNAME=	dxflib-3.26.4
PKGNAME=	dxflib-3.26.4
CATEGORIES=	cad
MASTER_SITES=	https://deb.debian.org/debian/pool/main/d/dxflib/
DISTFILES=	dxflib_3.26.4.orig.tar.gz
WRKSRC=		${WRKDIR}/dxflib-3.26.4
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://qcad.org/en/dxflib-downloads
COMMENT=	C++ library for reading and writing DXF files
LICENSE=	gnu-gpl-v2
USE_LANGUAGES=	c++
USE_CXX_FEATURES=	c++11
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
INSTALLATION_DIRS+=	share/licenses/dxflib
post-extract:
	${MKDIR} ${WRKSRC}/cmake
	${CP} ${FILESDIR}/dxflibConfig.cmake.in ${WRKSRC}/cmake/dxflibConfig.cmake.in
post-install:
	${INSTALL_DATA} ${WRKSRC}/gpl-2.0greater.txt ${DESTDIR}${PREFIX}/share/licenses/dxflib/LICENSE
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
