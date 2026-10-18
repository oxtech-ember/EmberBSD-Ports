# $NetBSD: Makefile,v 1.112 2026/09/01 09:04:13 adam Exp $
#
# When updating this, please also update devel/py-protobuf.
#
# NB: This package has very strange library versioning, lacking the
# usual libfoo.so.X symlink to libfoo.so.X.Y.  Thus, any change to the
# so version, e.g. .25.2.0 to .25.3.0, is an ABI change.  It is highly
# likely that any upstream release, even if apparently minor, will
# require a recursive revbump.

# Origin: EmberBSD (AI-assisted); current common provider with reviewed fixes.
DISTNAME=	protobuf-36.2
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=protocolbuffers/}
GITHUB_PROJECT=	protobuf
GITHUB_RELEASE=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/protocolbuffers/protobuf
COMMENT=	Google protocol buffers
LICENSE=	modified-bsd

GCC_REQD+=		16.2
USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++17
FORCE_CXX_STD=		c++17

# protobuf 34.1 failed to build with gcc <=12 and new abseil:
#   https://github.com/protocolbuffers/protobuf/issues/26383
# and thus we set GCC_REQD+=13.  As of 35.0, this is marked fixed in
# upstream NEWS, and the bug shows that fixes were merged.  Builds on
# NetBSD 10 with gcc10, which resolves linking failures in qgis4
# because of varying libstdc++, the usual tale of woe.
# Leaving this note for gc on July 1, in case this resurfaces somehow.

CMAKE_CONFIGURE_ARGS+=	-Dprotobuf_LOCAL_DEPENDENCIES_ONLY=ON
CMAKE_CONFIGURE_ARGS+=	-Dprotobuf_BUILD_SHARED_LIBS=ON
# requires googletest to be checked out in third_party/googletest
CMAKE_CONFIGURE_ARGS+=	-Dprotobuf_BUILD_TESTS=OFF

# illumos ld.so lazy PLT binding can invoke .init_array mid-init, re-entering
# a __cxa_guard-protected singleton and deadlocking.  protobuf generates these
# in .pb.cc files, so force BIND_NOW to resolve all PLT entries before init.
LDFLAGS.SunOS+=		-Wl,-z,now

# the [[ command will skip a test that would otherwise run
CHECK_PORTABILITY_SKIP+=	src/google/protobuf/compiler/zip_output_unittest.sh

.include "../../mk/bsd.prefs.mk"

.include "../../devel/cmake/build.mk"
#.include "../../devel/googletest/buildlink3.mk"
BUILDLINK_API_DEPENDS.abseil+=	abseil>=20260817.0nb2
.include "../../devel/abseil/buildlink3.mk"
BUILDLINK_API_DEPENDS.zlib+=	zlib>=1.3.2
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
