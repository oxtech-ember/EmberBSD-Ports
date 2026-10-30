# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= libtommath-1.3.0
CATEGORIES= math
MASTER_SITES= ${MASTER_SITE_GITHUB:=libtom/}
GITHUB_TAG= v${PKGVERSION_NOREV}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/libtom/libtommath/
COMMENT= Portable multiple-precision integer library
LICENSE= unlicense
USE_LANGUAGES= c
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=ON
TEST_TARGET= test
PLIST_VARS+= darwin unix
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
PLIST.darwin= yes
.else
PLIST.unix= yes
.endif
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
