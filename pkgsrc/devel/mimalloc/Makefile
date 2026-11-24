# $NetBSD: Makefile,v 1.18 2026/08/06 19:20:58 adam Exp $

DISTNAME=	mimalloc-3.7.0
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
PKGREVISION=	1
.endif
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=microsoft/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/microsoft/mimalloc
COMMENT=	General-purpose allocator with excellent performance characteristics
LICENSE=	mit

USE_CC_FEATURES=	c11
USE_CXX_FEATURES=	c++17
USE_LANGUAGES=		c c++
TEST_ENV+=		LD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}
# For Darwin
TEST_ENV+=		DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}
TEST_TARGET=		test
# For building tests.
LDFLAGS.NetBSD+=	-lpthread

CMAKE_CONFIGURE_ARGS+=	-DMI_INSTALL_TOPLEVEL=ON
# Rust tests use the same recipe sources and the common explicit Cargo owner.
CARGO_WRKSRC=		${WRKSRC}/contrib/rust
CMAKE_CONFIGURE_ARGS+=	-DMI_CARGO_COMMAND:STRING=${CARGO:Q}
CMAKE_CONFIGURE_ARGS+=	-DMI_CARGO_OPTIONS:STRING=--offline\;--locked\;-j${_MAKE_JOBS_N}

post-extract:
	${CP} ${FILESDIR}/Cargo.lock ${CARGO_WRKSRC}/Cargo.lock

INSTALLATION_DIRS+=	lib/cmake/mimalloc

PLIST_VARS+=	darwin-embed
.if ${OPSYS} == "Darwin"
PLIST.darwin-embed=	yes
_MIMALLOC_EMBED_BUILD=	${WRKDIR}/cmake-embed

# Reuse the selected SDK and upstream's complete MI_OVERRIDE=OFF configuration.
post-configure:
	cd ${WRKSRC} && ${SETENV} ${CONFIGURE_ENV} cmake \
	    --install-prefix ${PREFIX:Q} -B ${_MIMALLOC_EMBED_BUILD:Q} \
	    -G ${_CMAKE_BUILD_SYSTEM:Q} ${CMAKE_CONFIGURE_ARGS} \
	    -DMI_EMBED_LIBRARY=ON -DMI_OVERRIDE=OFF -DMI_BUILD_SHARED=ON \
	    -DMI_BUILD_STATIC=OFF -DMI_BUILD_OBJECT=OFF -DMI_BUILD_TESTS=OFF

post-build:
	${SETENV} ${MAKE_ENV} cmake --build ${_MIMALLOC_EMBED_BUILD:Q} \
	    --target mimalloc --parallel ${_MAKE_JOBS_N:U1}
.endif

post-install:
.if ${OPSYS} == "Darwin"
	${SETENV} ${INSTALL_ENV} DESTDIR=${DESTDIR:Q} cmake \
	    --install ${_MIMALLOC_EMBED_BUILD:Q} --component mimalloc-embed
.endif
	${RM} -f ${DESTDIR}${PREFIX}/lib/mimalloc.o

.include "options.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
do-test:
	${FAIL_MSG} "Run mimalloc C/Rust tests on the selected target; do not execute target binaries on the build host"
.endif

.include "../../devel/cmake/build.mk"
.include "cargo-depends.mk"
# Cargo uses libunwind only while building the optional Rust tests. The
# installed mimalloc libraries do not require the target runtime.
BUILDLINK_DEPMETHOD.libunwind= build
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
