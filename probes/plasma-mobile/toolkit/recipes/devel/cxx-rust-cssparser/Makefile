# Origin: EmberBSD (AI-assisted). First port; Union from Plasma 6.8 needs it.

DISTNAME=	cxx-rust-cssparser-1.1.0
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=KDE/}
GITHUB_TAG=	v1.1.0
EXTRACT_SUFX=	.tar.gz

# Offline crate sources generated on the host with `cargo vendor` from
# rust/Cargo.lock. Regenerate this archive when the crate set changes.
DISTFILES=	cxx-rust-cssparser-1.1.0.tar.gz cxx-rust-cssparser-vendor-1.1.0.tar.gz

HOMEPAGE=	https://invent.kde.org/libraries/cxx-rust-cssparser
COMMENT=	C++ CSS parsing API implemented through the Rust cssparser crate
LICENSE=	modified-bsd AND gnu-lgpl-v2.1 AND cc0-1.0-universal

.include "../../mk/bsd.prefs.mk"

USE_CMAKE=	yes
USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config ar
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+= -DBUILD_EXAMPLES=OFF

post-extract:
	${MV} ${WRKDIR}/vendor ${WRKSRC}/rust/vendor

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The host cargo driver builds the crate for the NetBSD target; the target
# std already lives in the host rustc sysroot and the wrapped GCC16 cross
# compilers serve as the linker and the C++ bridge compiler.
RUST_TARGET=	aarch64-unknown-netbsd
RUST_OUT=	${WRKDIR}/rust-out
BRIDGE_A=	${WRKDIR}/libcxx-rust-cssparser-impl-bridge.a
BRIDGE_INC=	${WRKDIR}/bridge-include
CARGO_ENV=	CARGO_HOME=${WRKDIR}/cargo-home
CARGO_ENV+=	CARGO_TARGET_DIR=${RUST_OUT}
CARGO_ENV+=	CARGO_TARGET_AARCH64_UNKNOWN_NETBSD_LINKER=${WRKDIR}/.cwrapper/bin/aarch64--netbsd-gcc
CARGO_ENV+=	CXX_aarch64_unknown_netbsd=${WRKDIR}/.cwrapper/bin/aarch64--netbsd-g++
CARGO_ENV+=	CC=/usr/bin/cc
CARGO_ENV+=	CXX=/usr/bin/c++
CARGO_ENV+=	CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc

pre-configure:
	@set -e; cd ${WRKSRC}/rust; \
	mkdir -p .cargo; \
	printf '[source.crates-io]\nreplace-with = "vendored-sources"\n\n[source.vendored-sources]\ndirectory = "vendor"\n' > .cargo/config.toml; \
	${SETENV} ${CARGO_ENV} ${EMBERBSD_CROSS_HOST_PREFIX}/bin/cargo build \
		--release --target ${RUST_TARGET} --offline; \
	bdir="$$(${FIND} ${RUST_OUT}/${RUST_TARGET}/release/build -path '*out/cxxbridge/sources' -type d | head -1 | sed 's|/out/cxxbridge/sources||')"; \
	[ -n "$$bdir" ] || { echo 'no cxxbridge output found' >&2; exit 1; }; \
	${RM} -rf ${BRIDGE_INC}; \
	${CP} -R $$bdir/out/cxxbridge/include ${BRIDGE_INC}; \
	${WRKDIR}/.cwrapper/bin/aarch64--netbsd-g++ -std=c++20 -fPIC -O2 \
		-Wno-maybe-uninitialized -I${BRIDGE_INC} \
		-c $$bdir/out/cxxbridge/sources/cxx-rust-cssparser-impl/src/ffi.rs.cc \
		-o ${WRKDIR}/bridge.o; \
	${AR} qc ${BRIDGE_A} ${WRKDIR}/bridge.o

CMAKE_CONFIGURE_ARGS+= -DEMBER_RUST_LIB=${RUST_OUT}/${RUST_TARGET}/release/libcxx_rust_cssparser_impl.a
CMAKE_CONFIGURE_ARGS+= -DEMBER_BRIDGE_LIB=${BRIDGE_A}
CMAKE_CONFIGURE_ARGS+= -DEMBER_BRIDGE_INCLUDE=${BRIDGE_INC}
.endif

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
