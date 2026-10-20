# $NetBSD$

# Upstream revision 2.3.6, pinned to commit 508cce97d983c4c61099ceacc11c984a60053967.
DISTNAME=	muparser-2.3.6
CATEGORIES=	math
MASTER_SITES=	https://github.com/beltoforion/muparser/archive/
DISTFILES=	508cce97d983c4c61099ceacc11c984a60053967.tar.gz
WRKSRC=		${WRKDIR}/muparser-508cce97d983c4c61099ceacc11c984a60053967

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/beltoforion/muparser/
COMMENT=	Fast math parser library for C and C++
LICENSE=	2-clause-bsd

USE_LANGUAGES=		c c++
USE_CXX_FEATURES+=	c++20

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=ON
CMAKE_CONFIGURE_ARGS+=	-DENABLE_OPENMP=ON
CMAKE_CONFIGURE_ARGS+=	-DENABLE_SAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib

# Cross builds compile the test executable. Run it only on the build host.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
TEST_TARGET=	test
.endif

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
