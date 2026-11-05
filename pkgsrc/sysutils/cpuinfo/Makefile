# $NetBSD: Makefile,v 1.4 2025/08/08 10:12:55 wiz Exp $

DISTNAME=	cpuinfo-0.0.20261104
CATEGORIES=	sysutils
MASTER_SITES=	${MASTER_SITE_GITHUB:=pytorch/}
GITHUB_TAG=	731932997e55e84900e6f95aefb6edd167b0edcc
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/pytorch/cpuinfo/
COMMENT=	CPU information library
LICENSE=	2-clause-bsd

USE_LANGUAGES+=		c c++
USE_CXX_FEATURES+=	c++17
FORCE_CXX_STD=		c++17
USE_TOOLS+=		pkg-config

.include "../../mk/bsd.prefs.mk"

PLIST_VARS+=		x86 elf darwin
.if ${MACHINE_ARCH} == "x86_64" || ${MACHINE_ARCH} == "i386"
PLIST.x86=		yes
.endif
.if ${OPSYS} == "Darwin"
PLIST.darwin=		yes
.else
PLIST.elf=		yes
.endif

PKGCONFIG_OVERRIDE=	libcpuinfo.pc.in
CMAKE_CONFIGURE_ARGS+=	-DCPUINFO_BUILD_STATIC_AND_SHARED=ON
CMAKE_CONFIGURE_ARGS+=	-DCPUINFO_BUILD_UNIT_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DCPUINFO_BUILD_MOCK_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DCPUINFO_BUILD_BENCHMARKS=OFF
CMAKE_CONFIGURE_ARGS+=	-DCPUINFO_PACKAGE_VERSION=${PKGVERSION_NOREV:Q}

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
