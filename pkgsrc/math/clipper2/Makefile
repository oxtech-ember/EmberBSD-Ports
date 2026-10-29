# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted); common Clipper2 provider.
DISTNAME= Clipper2-2.0.1
CATEGORIES= math
MASTER_SITES= ${MASTER_SITE_GITHUB:=AngusJohnson/}
GITHUB_PROJECT= Clipper2
GITHUB_TAG= Clipper2_${PKGVERSION_NOREV}
WRKSRC= ${WRKDIR}/Clipper2-${GITHUB_TAG}/CPP
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/AngusJohnson/Clipper2
COMMENT= Polygon clipping and offsetting library
LICENSE= boost-license
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON
CMAKE_CONFIGURE_ARGS+= -DCLIPPER2_UTILS=OFF
CMAKE_CONFIGURE_ARGS+= -DCLIPPER2_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+= -DCLIPPER2_TESTS=ON
CMAKE_CONFIGURE_ARGS+= -DUSE_EXTERNAL_GTEST=ON
CMAKE_CONFIGURE_ARGS+= -DCMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE=PRE_TEST
TEST_TARGET= test
.if ${OPSYS} == "Darwin"
TEST_ENV+= DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}
.endif
BUILDLINK_DEPMETHOD.googletest= build
.include "../../devel/googletest/buildlink3.mk"
PKGCONFIG_OVERRIDE+= Clipper2.pc.cmakein
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
