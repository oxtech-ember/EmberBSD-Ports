# Origin: desktop-app and wallet-engine contributors.
DISTNAME= wallet-engine-0.0.7
PKGNAME= tdesktop-rust-0.1.0
PKGREVISION= 3
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=i582/}
GITHUB_PROJECT= wallet-engine
GITHUB_TAG= e59e0d89d7ee90c388bf36e3334c5b276f396697
SITES.wallet-engine-0.0.7.tar.gz= -https://github.com/i582/wallet-engine/archive/${GITHUB_TAG}.tar.gz
DISTFILES= wallet-engine-0.0.7.tar.gz tlottie-1.0.6.tar.gz
SITES.tlottie-1.0.6.tar.gz= -https://github.com/dkaraush/tlottie/archive/refs/tags/v1.0.6.tar.gz
WRKSRC= ${WRKDIR}/wallet-engine-${GITHUB_TAG}
HOMEPAGE= https://github.com/i582/wallet-engine
COMMENT= Single Rust archive and bindings for desktop-app consumers
LICENSE= mit AND apache-2.0 AND modified-bsd AND mpl-2.0 AND unicode-v3
USE_LANGUAGES= c c++
USE_TOOLS+= bsdtar
RUST_REQ= 1.99.1
EMBER_CARGO_PATCH_SET= yes
CARGO_WRKSRC= ${WRKDIR}/provider
INSTALLATION_DIRS= lib lib/pkgconfig include/tlottie include/wallet_engine share/licenses/tdesktop-rust
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} share/licenses/tdesktop-rust -type f -print | ${SORT};
TOOL_DEPENDS+= uniffi-bindgen-cpp>=0.9.0:../../devel/uniffi-bindgen-cpp

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if ${MACHINE_ARCH} == "x86_64"
EMBER_CARGO_TARGET= x86_64-unknown-netbsd
TOOL_DEPENDS+= rust-std-x86_64-netbsd>=1.99.1:../../lang/rust-std-x86_64-netbsd
.elif ${MACHINE_ARCH} == "aarch64"
EMBER_CARGO_TARGET= aarch64-unknown-netbsd
TOOL_DEPENDS+= rust-std-aarch64-netbsd>=1.99.1:../../lang/rust-std-aarch64-netbsd
.else
PKG_FAIL_REASON+= "Select an existing shared Rust target std for this ABI"
.endif
.endif

post-extract:
	${MKDIR} ${CARGO_WRKSRC}/src
	${CP} ${FILESDIR}/Cargo.toml ${FILESDIR}/Cargo.lock ${CARGO_WRKSRC}/
	${CP} ${FILESDIR}/lib.rs ${CARGO_WRKSRC}/src/lib.rs
	${LN} -s ${WRKSRC} ${WRKDIR}/wallet-engine
	${LN} -s ${WRKDIR}/tlottie-1.0.6 ${WRKDIR}/tlottie
	${LN} -s ${CARGO_VENDOR_DIR}/ton-0.4.12 ${WRKDIR}/ton
	${MKDIR} ${WRKDIR}/crates
	${LN} -s ${CARGO_VENDOR_DIR}/crypto_box-0.9.1 ${WRKDIR}/crates/crypto_box-0.9.1
	${LN} -s ${CARGO_VENDOR_DIR}/crypto_secretbox-0.1.1 ${WRKDIR}/crates/crypto_secretbox-0.1.1
	${LN} -s ${CARGO_VENDOR_DIR}/curve25519-dalek-derive-0.1.1 ${WRKDIR}/crates/curve25519-dalek-derive-0.1.1
	${LN} -s ${CARGO_VENDOR_DIR}/darling_core-0.23.0 ${WRKDIR}/crates/darling_core-0.23.0
	${LN} -s ${CARGO_VENDOR_DIR}/darling_macro-0.23.0 ${WRKDIR}/crates/darling_macro-0.23.0
	${LN} -s ${CARGO_VENDOR_DIR}/deluxe-0.5.0 ${WRKDIR}/crates/deluxe-0.5.0
	${LN} -s ${CARGO_VENDOR_DIR}/deluxe-core-0.5.0 ${WRKDIR}/crates/deluxe-core-0.5.0
	${LN} -s ${CARGO_VENDOR_DIR}/deluxe-macros-0.5.0 ${WRKDIR}/crates/deluxe-macros-0.5.0
	${LN} -s ${CARGO_VENDOR_DIR}/derive_setters-0.1.9 ${WRKDIR}/crates/derive_setters-0.1.9
	${LN} -s ${CARGO_VENDOR_DIR}/strum_macros-0.28.0 ${WRKDIR}/crates/strum_macros-0.28.0
	${LN} -s ${CARGO_VENDOR_DIR}/ton_core-0.3.11 ${WRKDIR}/crates/ton_core-0.3.11
	${LN} -s ${CARGO_VENDOR_DIR}/ton_macros-0.2.6 ${WRKDIR}/crates/ton_macros-0.2.6
	${LN} -s ${CARGO_VENDOR_DIR}/uniffi_internal_macros-0.32.2 ${WRKDIR}/crates/uniffi_internal_macros-0.32.2
	${LN} -s ${CARGO_VENDOR_DIR}/uniffi_macros-0.32.2 ${WRKDIR}/crates/uniffi_macros-0.32.2
	${LN} -s ${CARGO_VENDOR_DIR}/chrono-0.4.45 ${WRKDIR}/crates/chrono-0.4.45
	${LN} -s ${CARGO_VENDOR_DIR}/parking_lot_core-0.9.12 ${WRKDIR}/crates/parking_lot_core-0.9.12
	${LN} -s ${CARGO_VENDOR_DIR}/scroll_derive-0.12.1 ${WRKDIR}/crates/scroll_derive-0.12.1
	${LN} -s ${CARGO_VENDOR_DIR}/windows-core-0.62.2 ${WRKDIR}/crates/windows-core-0.62.2
	${LN} -s ${CARGO_VENDOR_DIR}/windows-result-0.4.1 ${WRKDIR}/crates/windows-result-0.4.1
	${LN} -s ${CARGO_VENDOR_DIR}/windows-strings-0.5.1 ${WRKDIR}/crates/windows-strings-0.5.1
	${LN} -s ${CARGO_VENDOR_DIR}/windows-sys-0.61.2 ${WRKDIR}/crates/windows-sys-0.61.2

# Both patches belong to this shared source owner. Preserve upstream attribution.
post-patch:
	cd ${WRKSRC} && ${EMBER_CARGO_PREFIX}/bin/gpatch -p1 < ${FILESDIR}/desktop-app-wallet-engine.patch
	cd ${WRKSRC} && ${EMBER_CARGO_PREFIX}/bin/gpatch -p1 < ${FILESDIR}/wallet-ton-migration.patch

# Generate bindings from the target archive with the selected native tool.
do-build:
	cd ${CARGO_WRKSRC} && if ${SETENV} ${MAKE_ENV} ${CARGO} rustc --release --locked ${DEFAULT_CARGO_ARGS} --lib -- --crate-type staticlib --print native-static-libs > ${WRKDIR}/native-static-libs.log 2>&1; then ${CAT} ${WRKDIR}/native-static-libs.log; else ${CAT} ${WRKDIR}/native-static-libs.log; exit 1; fi
	${SED} -n 's/^note: native-static-libs: //p' ${WRKDIR}/native-static-libs.log > ${WRKDIR}/native-static-libs
	${TEST} `${WC} -l < ${WRKDIR}/native-static-libs` -eq 1 && ${TEST} -s ${WRKDIR}/native-static-libs
	cd ${CARGO_WRKSRC:Q} && target=${EMBER_CARGO_TARGET:Q}; if [ -z "$$target" ]; then target=`${EMBER_CARGO_PREFIX}/bin/rustc -vV | ${SED} -n 's/^host: //p'`; fi; \
	    lib=${EMBER_CARGO_OUTPUT}/$$target/release/libtdesktop_rust.a; \
	    ${TEST} -f "$$lib" || exit 1; ${MKDIR} ${WRKDIR}/bindings; ${SETENV} ${MAKE_ENV} CARGO_HOME=${EMBER_CARGO_CONFIG:H:Q} CARGO_NET_OFFLINE=true ${TOOLBASE}/bin/uniffi-bindgen-cpp --library --out-dir ${WRKDIR}/bindings "$$lib"

# Explicit only: compile the cross-target regression ELFs after package staging.
.PHONY: telegram-regressions
telegram-regressions:
	cd ${CARGO_WRKSRC:Q} && ${SETENV} ${MAKE_ENV} ${CARGO} rustc --release --locked ${DEFAULT_CARGO_ARGS} --lib --message-format=json -- --crate-type staticlib --print native-static-libs > ${WRKDIR}/active-artifacts.jsonl
	target=${EMBER_CARGO_TARGET:Q}; if [ -z "$$target" ]; then target=`${EMBER_CARGO_PREFIX}/bin/rustc -vV | ${SED} -n 's/^host: //p'`; fi; \
	    ${SETENV} ${MAKE_ENV} ${TOOL_PYTHONBIN} -B -I -S ${.CURDIR}/tests/build.py \
	    --work ${WRKDIR:Q} --cargo-output ${EMBER_CARGO_OUTPUT:Q} --target "$$target" --artifacts ${WRKDIR:Q}/active-artifacts.jsonl \
	    --rustc ${EMBER_CARGO_PREFIX:Q}/bin/rustc --cxx ${CXX:Q} --stage-prefix ${DESTDIR:Q}${PREFIX:Q}

# Separate optional feature test graph; never part of the provider build.
_CRYPTO_TEST_CRATES= base16ct-1.0.0 blake2-0.11.0 chacha20-0.10.2 rand_core-0.10.1 serdect-0.4.3
_CRYPTO_TEST_DISTFILES= ${_CRYPTO_TEST_CRATES:S/$/.crate/}
_CRYPTO_TEST_WORK?= ${WRKDIR}/crypto-feature-test
_CRYPTO_TEST_FIXTURES?= ${.CURDIR}/tests
EMBER_CRYPTO_TEST_RUSTFLAGS?=
.PHONY: telegram-crypto-features
telegram-crypto-features:
	${MKDIR} ${_CRYPTO_TEST_WORK}/vendor
	${MAKE} CARGO_CRATE_DEPENDS=${_CRYPTO_TEST_CRATES:Q} DISTFILES=${_CRYPTO_TEST_DISTFILES:Q} fetch checksum
	${MAKE} WRKDIR=${_CRYPTO_TEST_WORK:Q} CARGO_CRATE_DEPENDS=${_CRYPTO_TEST_CRATES:Q} EXTRACT_ONLY=${_CRYPTO_TEST_DISTFILES:Q} do-extract cargo-vendor-crates
	${TOOL_PYTHONBIN} -B -I -S ${_CRYPTO_TEST_FIXTURES}/prepare-crypto.py --work ${WRKDIR:Q} --test-work ${_CRYPTO_TEST_WORK:Q} --fixtures ${_CRYPTO_TEST_FIXTURES}
	cd ${_CRYPTO_TEST_WORK:Q} && for features in salsa_noalloc chacha_noalloc; do ${SETENV} ${MAKE_ENV} CARGO_HOME=${_CRYPTO_TEST_WORK:Q}/.cargo CARGO_NET_OFFLINE=true RUSTFLAGS=${EMBER_CRYPTO_TEST_RUSTFLAGS:Q} ${EMBER_CARGO_PREFIX}/bin/cargo check --release --locked --offline --no-default-features --features $$features -j${MAKE_JOBS} || exit $$?; done
	cd ${_CRYPTO_TEST_WORK:Q} && ${SETENV} ${MAKE_ENV} CARGO_HOME=${_CRYPTO_TEST_WORK:Q}/.cargo CARGO_NET_OFFLINE=true RUSTFLAGS=${EMBER_CRYPTO_TEST_RUSTFLAGS:Q} ${EMBER_CARGO_PREFIX}/bin/cargo build --release --locked --offline --all-features -j${MAKE_JOBS}


do-install:
	target=${EMBER_CARGO_TARGET:Q}; if [ -z "$$target" ]; then target=`${EMBER_CARGO_PREFIX}/bin/rustc -vV | ${SED} -n 's/^host: //p'`; fi; \
	    ${INSTALL_DATA} ${EMBER_CARGO_OUTPUT}/$$target/release/libtdesktop_rust.a ${DESTDIR}${PREFIX}/lib/
	printf 'prefix=%s\nlibdir=$${prefix}/lib\nincludedir=$${prefix}/include\n\nName: tdesktop-rust\nDescription: Combined desktop Rust provider\nVersion: 0.1.0\nLibs: -L$${libdir} -ltdesktop_rust\nLibs.private: %s\nCflags: -I$${includedir}\n' ${PREFIX:Q} "`${CAT} ${WRKDIR}/native-static-libs`" > ${DESTDIR}${PREFIX}/lib/pkgconfig/tdesktop-rust.pc
	${INSTALL_DATA} ${WRKDIR}/tlottie/include/tlottie.h ${DESTDIR}${PREFIX}/include/tlottie/
	${INSTALL_DATA} ${WRKDIR}/bindings/wallet_engine.hpp ${WRKDIR}/bindings/wallet_engine.cpp ${WRKDIR}/bindings/wallet_engine_scaffolding.hpp ${DESTDIR}${PREFIX}/include/wallet_engine/
	${INSTALL_DATA} ${WRKSRC}/LICENSE-APACHE ${WRKSRC}/LICENSE-MIT ${WRKDIR}/tlottie/LICENSE ${DESTDIR}${PREFIX}/share/licenses/tdesktop-rust/
	${INSTALL_DATA} ${WRKSRC}/bindgen/cpp/LICENSE ${DESTDIR}${PREFIX}/share/licenses/tdesktop-rust/MPL-2.0
	${MKDIR} ${DESTDIR}${PREFIX}/share/licenses/tdesktop-rust/crates
	cd ${CARGO_VENDOR_DIR} && ${FIND} . -type f \( -iname 'license*' -o -iname 'licence*' -o -iname 'copying*' -o -iname 'notice*' -o -name Cargo.toml \) -print | ${TOOLBASE}/bin/bsdtar -cf - -T - | (cd ${DESTDIR}${PREFIX}/share/licenses/tdesktop-rust/crates && ${TOOLBASE}/bin/bsdtar -xf -)

.include "cargo-depends.mk"
BUILDLINK_DEPMETHOD.libunwind= build
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../mk/bsd.pkg.mk"
