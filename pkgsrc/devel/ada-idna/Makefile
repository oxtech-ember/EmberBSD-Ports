# $NetBSD$
DISTNAME= idna-0.7.0
PKGNAME= ada-${DISTNAME}
PKGREVISION= 2
WRKSRC= ${WRKDIR}/${DISTNAME}
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=ada-url/}
GITHUB_PROJECT= idna
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/ada-url/idna
COMMENT= Unicode IDNA processing library
LICENSE= apache-2.0 OR mit
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++20
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON -DADA_USE_SIMDUTF=ON
BUILDLINK_PASSTHRU_RPATHDIRS+= ${WRKDIR}/${DISTNAME}/cmake-pkgsrc-build/src
TEST_TARGET= test
.include "../../mk/bsd.prefs.mk"
.include "../../mk/emberbsd-native-cxx-runtime.mk"
.if ${OPSYS} == "Darwin"
IDNA_LIB= libada-idna.dylib
IDNA_SOVERSION= libada-idna.0.dylib
IDNA_VERSIONED= libada-idna.0.7.0.dylib
.else
IDNA_LIB= libada-idna.so
IDNA_SOVERSION= libada-idna.so.0
IDNA_VERSIONED= libada-idna.so.0.7.0
.endif
PLIST_SUBST+= IDNA_LIB=${IDNA_LIB} IDNA_SOVERSION=${IDNA_SOVERSION} IDNA_VERSIONED=${IDNA_VERSIONED}
BUILDLINK_DEPMETHOD.googletest= build
BUILDLINK_DEPMETHOD.simdjson= build
.include "../../devel/googletest/buildlink3.mk"
.include "../../devel/simdjson/buildlink3.mk"
.include "../../devel/simdutf/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
