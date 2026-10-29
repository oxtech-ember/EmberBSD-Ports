# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= meshoptimizer-1.3
CATEGORIES= graphics
MASTER_SITES= ${MASTER_SITE_GITHUB:=zeux/}
GITHUB_TAG= v${PKGVERSION_NOREV}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/zeux/meshoptimizer/
COMMENT= Mesh optimization library
LICENSE= mit
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++11
CMAKE_CONFIGURE_ARGS+= -DCMAKE_POSITION_INDEPENDENT_CODE=ON
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
