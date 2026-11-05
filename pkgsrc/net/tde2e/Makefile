# $NetBSD$
# WIP: configure-only, PLIST and host generation must be proven.
DISTNAME= td-4c6377aa7386c39217878a9a56d581922ad37ca4
PKGNAME= tde2e-1.8.69
CATEGORIES= net
MASTER_SITES= -https://github.com/tdlib/td/archive/4c6377aa7386c39217878a9a56d581922ad37ca4.tar.gz
HOMEPAGE= https://github.com/tdlib/td/
COMMENT= End-to-end encryption library for Telegram clients
LICENSE= boost-license
USE_LANGUAGES= c c++
USE_TOOLS+= gperf
CMAKE_CONFIGURE_ARGS+= -DTD_E2E_ONLY=ON -DTD_INSTALL_STATIC_LIBRARIES=ON
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=OFF

# WIP cross producer: native selected SDK tools, target objects remain separate.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:tl} == "yes"
TOOLS_CREATE+= native-cc native-cxx native-ar
TOOLS_SCRIPT.native-cc= exec ${NATIVE_CC} "$$@"
TOOLS_SCRIPT.native-cxx= exec ${NATIVE_CXX} "$$@"
TOOLS_SCRIPT.native-ar= exec ${NATIVE_AR} "$$@"
_TD_NATIVE_DIR= ${WRKDIR}/.td-native-generator
pre-configure: tde2e-native-generated
.PHONY: tde2e-native-generated
tde2e-native-generated:
	${CMAKE} -S ${WRKSRC:Q} -B ${_TD_NATIVE_DIR:Q} -G Ninja \
	    -DCMAKE_C_COMPILER=${TOOLS_CMD.native-cc:Q} \
	    -DCMAKE_CXX_COMPILER=${TOOLS_CMD.native-cxx:Q} \
	    -DCMAKE_AR=${TOOLS_CMD.native-ar:Q} \
	    -DCMAKE_MAKE_PROGRAM=${EMBERBSD_CROSS_HOST_PREFIX:Q}/bin/ninja \
	    -DCMAKE_PREFIX_PATH=${EMBERBSD_CROSS_HOST_PREFIX:Q} \
	    -DCMAKE_C_FLAGS=${NATIVE_CPPFLAGS:U:Q}\ ${NATIVE_CFLAGS:U:Q} \
	    -DCMAKE_CXX_FLAGS=${NATIVE_CPPFLAGS:U:Q}\ ${NATIVE_CXXFLAGS:U:Q} \
	    -DCMAKE_EXE_LINKER_FLAGS=${NATIVE_LDFLAGS:U:Q} \
	    -DTD_GENERATE_SOURCE_FILES=ON -DBUILD_TESTING=OFF
	${CMAKE} --build ${_TD_NATIVE_DIR:Q} --target prepare_cross_compiling --parallel ${_MAKE_JOBS_N:Q}
	${TEST} -f ${WRKSRC:Q}/td/generate/auto/td/telegram/e2e_api.cpp
.endif

.include "../../security/openssl/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
