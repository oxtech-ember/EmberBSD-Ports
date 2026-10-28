# $NetBSD$
DISTNAME= uvwasi-0.0.23
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=nodejs/}
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/nodejs/uvwasi
COMMENT= WASI syscall API built on libuv
LICENSE= mit
USE_LANGUAGES= c
USE_TOOLS+= pkg-config
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=ON
TEST_TARGET= test
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
UVWASI_SHARED= libuvwasi.dylib
UVWASI_SONAME= libuvwasi.0.dylib
UVWASI_VERSIONED= libuvwasi.${PKGVERSION_NOREV}.dylib
.else
UVWASI_SHARED= libuvwasi.so
UVWASI_SONAME= libuvwasi.so.0
UVWASI_VERSIONED= libuvwasi.so.${PKGVERSION_NOREV}
.endif
PLIST_SUBST+= UVWASI_SHARED=${UVWASI_SHARED} UVWASI_SONAME=${UVWASI_SONAME} UVWASI_VERSIONED=${UVWASI_VERSIONED}
.include "../../devel/libuv/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
