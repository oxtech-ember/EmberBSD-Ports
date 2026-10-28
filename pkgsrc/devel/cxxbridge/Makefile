# Origin: EmberBSD (AI-assisted). Shared CXX generator and matching header.
DISTNAME= cxxbridge-cmd-1.0.205
PKGNAME= cxxbridge-1.0.205
CATEGORIES= devel
MASTER_SITES= https://static.crates.io/crates/cxxbridge-cmd/
EXTRACT_SUFX= .crate
HOMEPAGE= https://cxx.rs/
COMMENT= Rust CXX bridge generator and matching C++ header
LICENSE= mit AND apache-2.0 AND unicode-v3

USE_LANGUAGES= c c++
USE_TOOLS+= bsdtar
RUST_REQ= 1.99.1
EMBER_CARGO_PATCH_SET= yes
CARGO_ARGS= build --release --locked ${DEFAULT_CARGO_ARGS}
CARGO_INSTALL_ARGS= install --path . --locked --no-track --root ${DESTDIR}${PREFIX} --target-dir ${EMBER_CARGO_OUTPUT} ${DEFAULT_CARGO_ARGS}
RUSTFLAGS+= --remap-path-prefix=${WRKDIR}=.
INSTALLATION_DIRS= bin include/rust share/licenses/cxxbridge
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} share/licenses/cxxbridge -type f -print | ${SORT};

post-extract:
	${CP} ${FILESDIR}/Cargo.lock ${WRKSRC}/Cargo.lock

do-test:
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${FAIL_MSG} "Run cxxbridge tests on the selected target, not the build host"
.else
	cd ${CARGO_WRKSRC} && ${SETENV} ${TEST_ENV} ${MAKE_ENV} ${CARGO} test --release --locked ${DEFAULT_CARGO_ARGS}
	cd ${CARGO_WRKSRC} && ${SETENV} ${TEST_ENV} ${MAKE_ENV} ${CARGO} run --release --locked ${DEFAULT_CARGO_ARGS} -- --header > ${WRKDIR}/generated-cxx.h
	${CMP} ${WRKDIR}/generated-cxx.h ${CARGO_VENDOR_DIR}/cxx-1.0.205/include/cxx.h
.endif

post-install:
	${INSTALL_DATA} ${CARGO_VENDOR_DIR}/cxx-1.0.205/include/cxx.h ${DESTDIR}${PREFIX}/include/rust/cxx.h
	${INSTALL_DATA} ${WRKSRC}/LICENSE-APACHE ${WRKSRC}/LICENSE-MIT ${DESTDIR}${PREFIX}/share/licenses/cxxbridge
	${MKDIR} ${DESTDIR}${PREFIX}/share/licenses/cxxbridge/crates
	cd ${CARGO_VENDOR_DIR} && ${FIND} . -type f \( -iname 'license*' -o -iname 'licence*' -o -iname 'copying*' -o -iname 'notice*' -o -name Cargo.toml \) -print | ${TOOLBASE}/bin/bsdtar -cf - -T - | (cd ${DESTDIR}${PREFIX}/share/licenses/cxxbridge/crates && ${TOOLBASE}/bin/bsdtar -xf -)

.include "cargo-depends.mk"
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../mk/bsd.pkg.mk"
