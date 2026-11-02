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
.include "../../mk/bsd.prefs.mk"

.if ${EMBERBSD_NATIVE_BOOTSTRAP:Uno} == "yes" && ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.error "EMBERBSD_NATIVE_BOOTSTRAP cannot be used for cross builds"
.endif

PLIST_VARS+=	cmake
.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} == "yes" || ${EMBERBSD_NATIVE_BOOTSTRAP:Uno} == "yes"
# Initial native bootstrap breaks cmake -> libarchive -> zstd -> lz4 by
# using upstream GNU Make. This omits the CMake package files.
USE_TOOLS+=	gmake
NO_CONFIGURE=	yes
BUILD_TARGET=	lib-release lz4-release
MAKE_FLAGS+=	PREFIX=${PREFIX} MANDIR=${PREFIX}/${PKGMANDIR}
MAKE_FLAGS+=	CC=${CC:Q} AR=${AR:Q} V=1
INSTALL_MAKE_FLAGS+=	${MAKE_FLAGS} DESTDIR=${DESTDIR}
.else
PLIST.cmake=	yes
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_MANDIR=man
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib
CONFIGURE_DIR=	build/cmake
.endif

post-install:
	${SH} ${FILESDIR}/install-stage.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} != "yes" && ${EMBERBSD_NATIVE_BOOTSTRAP:Uno} != "yes"
.include "../../devel/cmake/build.mk"
.endif
.include "../../mk/bsd.pkg.mk"
