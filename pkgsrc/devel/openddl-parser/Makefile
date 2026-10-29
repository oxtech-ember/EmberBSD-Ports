# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted); shared OpenDDL parser.
DISTNAME= openddl-parser-0.5.2
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=kimkulling/}
GITHUB_TAG= v${PKGVERSION_NOREV}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/kimkulling/openddl-parser/
COMMENT= Parser for Open Data Description Language
LICENSE= mit

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 1
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++11
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON -DDDL_BUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DDDL_BUILD_TESTS=ON -DDDL_BUILD_PARSER_DEMO=OFF
TEST_TARGET= test
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
TEST_ENV+= LD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/lib
TEST_ENV+= DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/lib
.endif
.include "../../devel/cmake/build.mk"
BUILDLINK_DEPMETHOD.googletest= build
.include "../../devel/googletest/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
