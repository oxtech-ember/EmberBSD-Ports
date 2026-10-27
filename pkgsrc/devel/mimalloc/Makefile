# $NetBSD: Makefile,v 1.18 2026/08/06 19:20:58 adam Exp $

DISTNAME=	mimalloc-3.6.0
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

post-install:
	${RM} -f ${DESTDIR}${PREFIX}/lib/mimalloc.o

.include "options.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
do-test:
	${FAIL_MSG} "Run mimalloc C/Rust tests on the selected target; do not execute target binaries on the build host"
.endif

.include "../../devel/cmake/build.mk"
.include "cargo-depends.mk"
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
