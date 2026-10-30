# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= yoga-3.2.1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=facebook/}
GITHUB_TAG= v${PKGVERSION_NOREV}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://www.yogalayout.dev/
COMMENT= Cross-platform Flexbox layout library
LICENSE= mit
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++20
CMAKE_CONFIGURE_ARGS+= -DYOGA_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+= -DCMAKE_POSITION_INDEPENDENT_CODE=ON
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
