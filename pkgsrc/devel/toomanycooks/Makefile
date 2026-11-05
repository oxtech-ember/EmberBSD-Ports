# $NetBSD$
DISTNAME= TooManyCooks-1.6.1
PKGNAME= toomanycooks-1.6.1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=tzcnt/}
GITHUB_PROJECT= TooManyCooks
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/tzcnt/TooManyCooks
COMMENT= C++20 coroutine concurrency framework
LICENSE= boost-license
USE_LANGUAGES= c c++
USE_CXX_FEATURES+= c++20
CMAKE_CONFIGURE_ARGS+= -DTMC_USE_HWLOC=ON
.include "../../devel/cmake/build.mk"
.include "../../parallel/hwloc/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
