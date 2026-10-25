# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= simplecpp-1.9.1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=cppcheck-opensource/}
GITHUB_PROJECT= simplecpp
GITHUB_TAG= ${PKGVERSION_NOREV}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/cppcheck-opensource/simplecpp
COMMENT= C and C++ preprocessor with token and macro provenance
LICENSE= 0-clause-bsd

USE_LANGUAGES= c++
USE_CXX_FEATURES= c++17
CMAKE_CONFIGURE_ARGS+= -DCMAKE_CXX_STANDARD:STRING=17
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS:BOOL=ON
TEST_TARGET= test

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
