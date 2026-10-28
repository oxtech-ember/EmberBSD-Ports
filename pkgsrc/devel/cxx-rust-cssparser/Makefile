# Origin: EmberBSD (AI-assisted). First port; Union from Plasma 6.8 needs it.

DISTNAME=	cxx-rust-cssparser-1.1.0
PKGREVISION=	3
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=KDE/}
GITHUB_TAG=	v1.1.0
EXTRACT_SUFX=	.tar.gz

HOMEPAGE=	https://invent.kde.org/libraries/cxx-rust-cssparser
COMMENT=	C++ CSS parsing API implemented through the Rust cssparser crate
# Components use AND; alternatives stay within each component's expression.
# The installed licenses.json records upstream SPDX expressions.
LICENSE=	2-clause-bsd AND cc0-1.0-universal AND gnu-lgpl-v2.1 AND \
		apache-2.0 AND mit AND mpl-2.0 AND zlib AND \
		(mit OR apache-2.0) AND (unlicense OR mit) AND \
		((mit OR apache-2.0) AND unicode-v3)

.include "../../mk/bsd.prefs.mk"

USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config
TOOL_DEPENDS+=	rust-bin>=1.99.1:../../lang/rust-bin
RUST_TYPE=	native
CARGO_WRKSRC=	${WRKSRC}/rust
RUST_REQ=	1.99.1
PYTHON_VERSIONS_ACCEPTED=	315
PYTHON_FOR_BUILD_ONLY=	tool
EMBER_CARGO_PATCH_SET=	yes
INSTALLATION_DIRS+=	share/licenses/cxx-rust-cssparser
GENERATE_PLIST+=	cd ${DESTDIR}${PREFIX}; ${FIND} share/licenses/cxx-rust-cssparser -type f -print | ${SORT};
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+= -DBUILD_EXAMPLES=OFF

# Preserve CMake build/install targets before including the shared Cargo vendor.
.include "../../devel/cmake/build.mk"
.include "cargo-depends.mk"
.include "../../lang/python/tool.mk"
.include "../../lang/rust/emberbsd-cargo.mk"

post-install:
	${TOOL_PYTHONBIN} -B -I -S ${FILESDIR}/install-notices.py \
	    --source ${WRKSRC:Q} --vendor ${CARGO_VENDOR_DIR:Q} \
	    --output ${DESTDIR}${PREFIX}/share/licenses/cxx-rust-cssparser

.include "cross.mk"

EMBER_CARGO_TARGET= ${RUST_TARGET:U}
EMBER_CARGO_HOST_CC= ${_EMBER_CSS_HOST_CC}
EMBER_CARGO_HOST_CXX= ${_EMBER_CSS_HOST_CXX}
EMBER_CARGO_HOST_AR= ${_EMBER_CSS_HOST_AR}
EMBER_CARGO_HOST_LINKER_LAUNCHER= ${EMBERBSD_DARWIN_LINKER_LAUNCHER:U}
RUST_OUT= ${EMBER_CARGO_OUTPUT}
BRIDGE_A= ${WRKDIR}/libcxx-rust-cssparser-impl-bridge.a
BRIDGE_INC= ${WRKDIR}/bridge-include
CMAKE_CONFIGURE_ARGS+= -DEMBER_RUST_LIB=${WRKDIR}/libcxx-rust-cssparser-impl.a
CMAKE_CONFIGURE_ARGS+= -DEMBER_BRIDGE_LIB=${BRIDGE_A}
CMAKE_CONFIGURE_ARGS+= -DEMBER_BRIDGE_INCLUDE=${BRIDGE_INC}

pre-configure: ember-css-build-bridge
.PHONY: ember-css-build-bridge
ember-css-build-bridge: ember-cargo-configure ember-css-check-cross
	${RUN} ${SETENV} ${CONFIGURE_ENV} ${TOOL_PYTHONBIN} -B -I -S ${FILESDIR:Q}/build-bridge.py \
	    --cargo ${_EMBER_CSS_PREFIX:Q}/bin/cargo --cargo-helper ${_PKGSRCDIR:Q}/lang/rust/emberbsd-cargo-config.py \
	    --config ${EMBER_CARGO_CONFIG:Q} --source ${WRKSRC:Q}/rust --work ${WRKDIR:Q} \
	    --bridge ${BRIDGE_A:Q} --include ${BRIDGE_INC:Q} --jobs ${_MAKE_JOBS_N:U1}

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
