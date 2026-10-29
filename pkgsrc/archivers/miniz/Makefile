# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted); common miniz provider.
DISTNAME= miniz-3.1.2
CATEGORIES= archivers
MASTER_SITES= ${MASTER_SITE_GITHUB:=richgel999/}
GITHUB_TAG= ${PKGVERSION_NOREV}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/richgel999/miniz
COMMENT= Compression and ZIP archive library
LICENSE= mit
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++20
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DBUILD_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTS=ON
TEST_TARGET= test
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
TEST_ENV+= DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}
.endif
BUILDLINK_DEPMETHOD.catch2= build
.include "../../devel/catch2/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
