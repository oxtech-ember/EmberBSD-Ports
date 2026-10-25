# $NetBSD$
DISTNAME=	libiio-1.0.0
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=analogdevicesinc/}
GITHUB_TAG=	v${PKGVERSION_NOREV}
DISTFILES=	${DEFAULT_DISTFILES} libiio-0.26-iio.h
SITES.libiio-0.26-iio.h=	-https://raw.githubusercontent.com/analogdevicesinc/libiio/a0eca0d2bf10326506fb762f0eec14255b27bef5/iio.h
EXTRACT_ONLY=	${DEFAULT_DISTFILES}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/analogdevicesinc/libiio
COMMENT=	Industrial I/O with USB and official ABI 0 compatibility
LICENSE=	gnu-lgpl-v2.1 AND gnu-gpl-v2 AND mit
GCC_REQD+=	16.2
USE_LANGUAGES=	c
USE_TOOLS+=	pkg-config
CMAKE_CONFIGURE_ARGS+=	-C ${FILESDIR}/receiver.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
INSTALLATION_DIRS+=	include/iio-compat-0 share/doc/libiio
post-install:
	${INSTALL_DATA} ${WRKSRC}/${CMAKE_BUILD_DIR}/iio-config.h ${DESTDIR}${PREFIX}/share/doc/libiio/iio-config.h
	${INSTALL_DATA} ${DISTDIR}/libiio-0.26-iio.h ${DESTDIR}${PREFIX}/include/iio-compat-0/iio.h
	${INSTALL_DATA} ${WRKSRC}/COPYING.txt ${DESTDIR}${PREFIX}/share/doc/libiio/COPYING.txt
	${INSTALL_DATA} ${WRKSRC}/COPYING_MIT.txt ${DESTDIR}${PREFIX}/share/doc/libiio/COPYING_MIT.txt
	${INSTALL_DATA} ${WRKSRC}/COPYING_GPL.txt ${DESTDIR}${PREFIX}/share/doc/libiio/COPYING_GPL.txt

.include "../../devel/cmake/build.mk"
BUILDLINK_API_DEPENDS.libusb1+=	libusb1>=1.0.30nb1
.include "../../devel/libusb1/buildlink3.mk"
BUILDLINK_API_DEPENDS.libxml2+=	libxml2>=2.15.4nb1
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
