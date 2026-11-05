# $NetBSD: Makefile,v 1.13 2026/06/30 20:10:22 adam Exp $

DISTNAME=	minizip-ng-4.2.2
PKGREVISION=	1
# Classic minizip installs the same source-facing names.
CONFLICTS+=	minizip-[0-9]*
CATEGORIES=	archivers
MASTER_SITES=	${MASTER_SITE_GITHUB:=zlib-ng/}
GITHUB_PROJECT=	minizip-ng
GITHUB_TAG=	${PKGVERSION_NOREV}

MAINTAINER=	ryoon@NetBSD.org
HOMEPAGE=	https://github.com/zlib-ng/minizip-ng
COMMENT=	Zip manipulation library written in C
LICENSE=	zlib

USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config

PKGCONFIG_OVERRIDE=	minizip.pc.cmakein

CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=YES
CMAKE_CONFIGURE_ARGS+=	-DMZ_COMPAT=YES -DMZ_LIB_SUFFIX=-ng
CMAKE_CONFIGURE_ARGS+=	-DMZ_LIBCOMP=OFF -DMZ_ZLIB_FLAVOR=zlib
CMAKE_CONFIGURE_ARGS+=	-DMZ_FETCH_LIBS=OFF -DMZ_FORCE_FETCH_LIBS=OFF
CMAKE_CONFIGURE_ARGS+=	-DMZ_PPMD=NO

# Selected zlib's original Windows compatibility callbacks; compiled only on Windows.
post-patch:
	${CP} ${FILESDIR}/iowin32.c ${FILESDIR}/iowin32.h ${WRKSRC}/compat/

# One implementation supplies both the modern namespace and classic source API.
INSTALLATION_DIRS+=	lib/cmake/minizip share/licenses/minizip-ng
post-install:
	cd ${DESTDIR}${PREFIX}/include && ${LN} -sfn minizip-ng minizip
	cd ${DESTDIR}${PREFIX}/lib && ${LN} -sfn libminizip-ng.${SHLIB_EXT} libminizip.${SHLIB_EXT}
	${SED} 's|^Cflags:|Cflags: -I$${includedir}/.. |' ${DESTDIR}${PREFIX}/lib/pkgconfig/minizip-ng.pc > ${DESTDIR}${PREFIX}/lib/pkgconfig/minizip.pc
	${INSTALL_DATA} ${FILESDIR}/minizip-config.cmake ${DESTDIR}${PREFIX}/lib/cmake/minizip/
	${INSTALL_DATA} ${DESTDIR}${PREFIX}/lib/cmake/minizip-ng/minizip-ng-config-version.cmake ${DESTDIR}${PREFIX}/lib/cmake/minizip/minizip-config-version.cmake
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/minizip-ng/LICENSE
	${INSTALL_DATA} ${FILESDIR}/MiniZip64_info.txt ${DESTDIR}${PREFIX}/share/licenses/minizip-ng/MiniZip64_info.txt

# Uses symlink(2) and _POSIX_C_SOURCE=200809L which NetBSD hides
CFLAGS.NetBSD+=	-D_NETBSD_SOURCE

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
# Resolve the selected prefix's shared dependencies in the installed dylib.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib
.endif
.include "../../devel/zlib/buildlink3.mk"
.include "../../archivers/bzip2/buildlink3.mk"
.include "../../archivers/xz/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../converters/libiconv/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
