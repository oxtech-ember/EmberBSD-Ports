# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= xatlas-20220725
CATEGORIES= graphics
MASTER_SITES= ${MASTER_SITE_GITHUB:=jpcy/}
GITHUB_PROJECT= xatlas
GITHUB_TAG= f700c7790aaa030e794b52ba7791a05c085faf0c
WRKSRC= ${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/jpcy/xatlas/
COMMENT= Mesh parameterization and UV unwrapping library
LICENSE= mit
PTHREAD_OPTS= require
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++11
CMAKE_CONFIGURE_ARGS+= -DCMAKE_POSITION_INDEPENDENT_CODE=ON
post-extract:
	${CP} ${FILESDIR}/CMakeLists.txt ${WRKSRC}/CMakeLists.txt
.include "../../mk/pthread.buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
