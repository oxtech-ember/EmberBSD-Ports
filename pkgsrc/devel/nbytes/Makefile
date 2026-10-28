# $NetBSD$
DISTNAME= nbytes-0.1.4
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=nodejs/}
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/nodejs/nbytes
COMMENT= Byte handling library from Node.js
LICENSE= mit
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++20
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON -DNBYTES_ENABLE_TESTING=ON
TEST_TARGET= test
# CMake discovers tests from the build tree before installation.
BUILDLINK_PASSTHRU_RPATHDIRS+= ${WRKDIR}/${DISTNAME}/cmake-pkgsrc-build/src
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
NBYTES_LIB= libnbytes.dylib
.else
NBYTES_LIB= libnbytes.so
.endif
PLIST_SUBST+= NBYTES_LIB=${NBYTES_LIB}
BUILDLINK_DEPMETHOD.googletest= build
.include "../../devel/googletest/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
