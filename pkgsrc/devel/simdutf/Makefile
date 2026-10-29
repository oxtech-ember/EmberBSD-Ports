# $NetBSD$
DISTNAME= simdutf-9.3.3
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=simdutf/}
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/simdutf/simdutf
COMMENT= SIMD-accelerated Unicode and base64
LICENSE= mit
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++20
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON -DSIMDUTF_TESTS=ON -DSIMDUTF_CXX_STANDARD=20 -DSIMDUTF_ATOMIC_BASE64_TESTS=ON
BUILDLINK_PASSTHRU_RPATHDIRS+= ${WRKDIR}/${DISTNAME}/cmake-pkgsrc-build/src
TEST_TARGET= test
.include "../../mk/bsd.prefs.mk"
.include "../../mk/emberbsd-native-cxx-runtime.mk"
.if ${OPSYS} == "Darwin"
SIMDUTF_LIB= libsimdutf.dylib
SIMDUTF_SOVERSION= libsimdutf.37.dylib
SIMDUTF_VERSIONED= libsimdutf.37.0.0.dylib
.else
SIMDUTF_LIB= libsimdutf.so
SIMDUTF_SOVERSION= libsimdutf.so.37
SIMDUTF_VERSIONED= libsimdutf.so.37.0.0
.endif
PLIST_SUBST+= SIMDUTF_LIB=${SIMDUTF_LIB} SIMDUTF_SOVERSION=${SIMDUTF_SOVERSION} SIMDUTF_VERSIONED=${SIMDUTF_VERSIONED}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} lib/cmake/simdutf -name "simdutfTargets-*.cmake" -type f -print | ${SORT};
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
