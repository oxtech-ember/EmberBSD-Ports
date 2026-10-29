# $NetBSD$

DISTNAME=	tinyexr-3.2.0
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_GITHUB:=syoyo/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/syoyo/tinyexr
COMMENT=	OpenEXR image reader and writer
LICENSE=	modified-bsd

USE_LANGUAGES=	c c++
USE_CXX_FEATURES=	c++11
USE_CMAKE=	yes
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

post-extract:
	${CP} ${FILESDIR}/CMakeLists.txt ${WRKSRC}/CMakeLists.txt
	${CP} ${FILESDIR}/legacy.cc ${WRKSRC}/legacy.cc
	${CP} ${FILESDIR}/TinyEXRConfig.cmake.in ${WRKSRC}/TinyEXRConfig.cmake.in

.include "../../archivers/zstd/buildlink3.mk"
.include "../../devel/libdeflate/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
