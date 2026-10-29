# $NetBSD$
# Origin: Assimp 6.0.5 Open3DGC snapshot; common EmberBSD provider.
DISTNAME= assimp-6.0.5
DIST_SUBDIR= open3dgc/assimp-6.0.5
PKGNAME= open3dgc-0.0.20260430
CATEGORIES= math
MASTER_SITES= ${MASTER_SITE_GITHUB:=assimp/}
GITHUB_PROJECT= assimp
GITHUB_TAG= v6.0.5
WRKSRC= ${WRKDIR}/${DISTNAME}/contrib/Open3DGC
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/assimp/assimp
COMMENT= Open 3D graphics geometry compression library
LICENSE= mit AND 2-clause-bsd
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++11
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON
TEST_TARGET= test
.if ${OPSYS} == "Darwin"
TEST_ENV+= DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}
.endif
post-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/licenses/open3dgc
	${INSTALL_DATA} ${FILESDIR:Q}/LICENSE-MIT ${DESTDIR:Q}${PREFIX:Q}/share/licenses/open3dgc/
	${INSTALL_DATA} ${FILESDIR:Q}/LICENSE-BSD-2-Clause ${DESTDIR:Q}${PREFIX:Q}/share/licenses/open3dgc/
post-extract:
	${CP} ${FILESDIR}/CMakeLists.txt ${WRKSRC}/CMakeLists.txt
	${CP} ${FILESDIR}/open3dgcConfig.cmake ${WRKSRC}/open3dgcConfig.cmake
	${CP} ${FILESDIR}/roundtrip.cpp ${WRKSRC}/roundtrip.cpp
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
