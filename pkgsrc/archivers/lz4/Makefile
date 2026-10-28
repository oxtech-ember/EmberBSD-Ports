# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), current common LZ4 package.
DISTNAME=	lz4-1.10.0
PKGREVISION=	1
CATEGORIES=	archivers
# The official v1.10.0 release archive (tag commit ebb370ca) matches distinfo.
MASTER_SITES=	${MASTER_SITE_GITHUB:=lz4/}
GITHUB_RELEASE=	v${PKGVERSION_NOREV}

HOMEPAGE=	https://lz4.org/
COMMENT=	Fast lossless compression library and command line tools
LICENSE=	2-clause-bsd AND gnu-gpl-v2

USE_LANGUAGES=	c
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_MANDIR=man
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib
CONFIGURE_DIR=	build/cmake

post-install:
	${SH} ${FILESDIR}/install-stage.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
