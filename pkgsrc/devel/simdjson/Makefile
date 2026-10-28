# $NetBSD$
DISTNAME= simdjson-5.0.6
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=simdjson/}
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/simdjson/simdjson
COMMENT= SIMD-accelerated JSON parser
LICENSE= apache-2.0
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON -DSIMDJSON_DEVELOPER_MODE=OFF -DSIMDJSON_ENABLE_THREADS=ON
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
SIMDJSON_LIB= libsimdjson.dylib
SIMDJSON_SOVERSION= libsimdjson.34.dylib
SIMDJSON_VERSIONED= libsimdjson.34.0.0.dylib
.else
SIMDJSON_LIB= libsimdjson.so
SIMDJSON_SOVERSION= libsimdjson.so.34
SIMDJSON_VERSIONED= libsimdjson.so.34.0.0
.endif
PLIST_SUBST+= SIMDJSON_LIB=${SIMDJSON_LIB} SIMDJSON_SOVERSION=${SIMDJSON_SOVERSION} SIMDJSON_VERSIONED=${SIMDJSON_VERSIONED}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} lib/cmake/simdjson -name "simdjsonTargets-*.cmake" -type f -print | ${SORT};
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
