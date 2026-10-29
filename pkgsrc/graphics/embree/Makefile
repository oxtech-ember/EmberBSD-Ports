# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= embree-4.4.1
CATEGORIES= graphics
MASTER_SITES= ${MASTER_SITE_GITHUB:=RenderKit/}
GITHUB_PROJECT= embree
GITHUB_TAG= v${PKGVERSION_NOREV}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://www.embree.org/
COMMENT= CPU ray tracing kernels
LICENSE= apache-2.0

USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
CMAKE_CONFIGURE_ARGS+= -DEMBREE_TUTORIALS=OFF
CMAKE_CONFIGURE_ARGS+= -DEMBREE_FILTER_FUNCTION=ON
CMAKE_CONFIGURE_ARGS+= -DFETCHCONTENT_FULLY_DISCONNECTED=ON

PLIST_VARS+= darwin elf

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
PLIST.darwin= yes
.else
PLIST.elf= yes
.endif
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 1
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

.include "../../devel/cmake/build.mk"
.include "../../parallel/threadingbuildingblocks/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
