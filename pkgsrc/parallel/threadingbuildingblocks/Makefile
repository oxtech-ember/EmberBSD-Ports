# $NetBSD: Makefile,v 1.22 2026/07/23 12:28:40 prlw1 Exp $

DISTNAME=	oneTBB-2023.1.0
PKGREVISION=	1
PKGNAME=	${DISTNAME:S/oneTBB-/threadingbuildingblocks-/}
CATEGORIES=	parallel
MASTER_SITES=	${MASTER_SITE_GITHUB:=uxlfoundation/}
GITHUB_PROJECT=	oneTBB
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	asau@inbox.ru
HOMEPAGE=	https://uxlfoundation.github.io/oneTBB/
COMMENT=	Threading Buildling Blocks
LICENSE=	apache-2.0

USE_TOOLS+=		pkg-config
USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++11

# Use one build directory across platforms.
CMAKE_CONFIGURE_ARGS+=	-DTBB_OUTPUT_DIR_BASE=pkgsrc
CMAKE_CONFIGURE_ARGS+=	-DTBB_STRICT=OFF
CMAKE_CONFIGURE_ARGS+=	-DTBB_DISABLE_HWLOC_AUTOMATIC_SEARCH=OFF

BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,--version-script=${WRKSRC}/src/tbb/def/lin64-tbb.def
BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,--version-script=${WRKSRC}/src/tbbmalloc/def/lin64-tbbmalloc.def
BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,--version-script=${WRKSRC}/src/tbbmalloc_proxy/def/lin64-proxy.def

.include "../../mk/bsd.prefs.mk"

.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

PLIST_VARS+=	lp32 lp64 proxy
.if ${OPSYS} == "NetBSD"
CMAKE_CONFIGURE_ARGS+=	-DTBBMALLOC_PROXY_BUILD=OFF
.else
PLIST.proxy=	yes
.endif
.if !empty(LP32PLATFORMS:@.PLAT.@${MACHINE_PLATFORM:M${.PLAT.}}@)
PLIST.lp32=	yes
.else
PLIST.lp64=	yes
.endif

.include "options.mk"
.include "../../devel/cmake/build.mk"
.include "../../parallel/hwloc/buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
