# $NetBSD$
DISTNAME= ada-4.0.0
PKGREVISION= 2
PKGNAME= ada-url-4.0.0
WRKSRC= ${WRKDIR}/${DISTNAME}
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=ada-url/}
GITHUB_PROJECT= ada
GITHUB_TAG= v4.0.0
HOMEPAGE= https://github.com/ada-url/ada
COMMENT= WHATWG URL parser and URLPattern library
LICENSE= apache-2.0 OR mit
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++20
ADA_PORTS_TESTING?= OFF
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON -DADA_TESTING=${ADA_PORTS_TESTING}
BUILDLINK_PASSTHRU_RPATHDIRS+= ${WRKDIR}/${DISTNAME}/cmake-pkgsrc-build/src
TEST_TARGET= test
.include "../../mk/bsd.prefs.mk"
.include "../../mk/emberbsd-native-cxx-runtime.mk"
.if ${OPSYS} == "Darwin"
ADA_LIB= libada.dylib
ADA_SOVERSION= libada.4.dylib
ADA_VERSIONED= libada.4.0.0.dylib
.else
ADA_LIB= libada.so
ADA_SOVERSION= libada.so.4
ADA_VERSIONED= libada.so.4.0.0
.endif
PLIST_SUBST+= ADA_LIB=${ADA_LIB} ADA_SOVERSION=${ADA_SOVERSION} ADA_VERSIONED=${ADA_VERSIONED}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} lib/cmake/ada -name "ada_targets-*.cmake" -type f -print | ${SORT};
.if ${ADA_PORTS_TESTING:tu} == "ON"
BUILDLINK_DEPMETHOD.googletest= build
BUILDLINK_DEPMETHOD.simdjson= build
.include "../../devel/googletest/buildlink3.mk"
.include "../../devel/simdjson/buildlink3.mk"
.endif
.include "../../devel/ada-idna/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
