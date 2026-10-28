# $NetBSD$
.include "../../www/llhttp/Makefile.common"
COMMENT= HTTP request and response parser
USE_LANGUAGES= c c++
CMAKE_CONFIGURE_ARGS+= -DLLHTTP_BUILD_SHARED_LIBS=ON -DLLHTTP_BUILD_STATIC_LIBS=OFF
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
LLHTTP_LIB= libllhttp.dylib
LLHTTP_SOVERSION= libllhttp.9.4.dylib
LLHTTP_VERSIONED= libllhttp.9.4.3.dylib
.else
LLHTTP_LIB= libllhttp.so
LLHTTP_SOVERSION= libllhttp.so.9.4
LLHTTP_VERSIONED= libllhttp.so.9.4.3
.endif
PLIST_SUBST+= LLHTTP_LIB=${LLHTTP_LIB} LLHTTP_SOVERSION=${LLHTTP_SOVERSION} LLHTTP_VERSIONED=${LLHTTP_VERSIONED}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} lib/cmake/llhttp -name "llhttp-targets-*.cmake" -type f -print | ${SORT};
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
