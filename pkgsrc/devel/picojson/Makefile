# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= picojson-111c9be5188f7350c2eac9ddaedd8cca3d7bf394
PKGNAME= picojson-1.3.0.20210117
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=kazuho/}
GITHUB_PROJECT= picojson
GITHUB_TAG= 111c9be5188f7350c2eac9ddaedd8cca3d7bf394

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/kazuho/picojson
COMMENT= Header-only C++ JSON parser and serializer
LICENSE= 2-clause-bsd

USE_LANGUAGES= c++
USE_CXX_FEATURES= c++11
CMAKE_CONFIGURE_ARGS+= -DCMAKE_CXX_STANDARD:STRING=11
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING:BOOL=ON
NO_ARCH= yes
TEST_TARGET= test

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
