# $NetBSD$
DISTNAME= merve-1.2.2
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=nodejs/}
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/nodejs/merve
COMMENT= Lexer for named exports in CommonJS modules
LICENSE= mit
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON -DMERVE_TESTING=ON -DMERVE_USE_SIMDUTF=ON
BUILDLINK_PASSTHRU_RPATHDIRS+= ${WRKDIR}/${DISTNAME}/cmake-pkgsrc-build/src
TEST_TARGET= test
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
MERVE_LIB= libmerve.dylib
MERVE_SOVERSION= libmerve.1.dylib
MERVE_VERSIONED= libmerve.1.2.2.dylib
.else
MERVE_LIB= libmerve.so
MERVE_SOVERSION= libmerve.so.1
MERVE_VERSIONED= libmerve.so.1.2.2
.endif
PLIST_SUBST+= MERVE_LIB=${MERVE_LIB} MERVE_SOVERSION=${MERVE_SOVERSION} MERVE_VERSIONED=${MERVE_VERSIONED}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} lib/cmake/merve -name "merve_targets-*.cmake" -type f -print | ${SORT};
BUILDLINK_DEPMETHOD.googletest= build
.include "../../devel/googletest/buildlink3.mk"
.include "../../devel/simdutf/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
