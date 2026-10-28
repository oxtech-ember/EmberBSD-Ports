# $NetBSD$
DISTNAME= uvwasi-0.0.23
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
.else
UVWASI_SHARED= libuvwasi.so
.endif
PLIST_SUBST+= UVWASI_SHARED=${UVWASI_SHARED}
.include "../../devel/libuv/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
