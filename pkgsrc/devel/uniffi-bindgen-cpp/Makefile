# Origin: wallet-engine contributors; shared host tool adaptation.
DISTNAME= wallet-engine-0.0.7
PKGNAME= uniffi-bindgen-cpp-0.9.0
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=i582/}
GITHUB_PROJECT= wallet-engine
GITHUB_TAG= e59e0d89d7ee90c388bf36e3334c5b276f396697
DISTFILES= wallet-engine-0.0.7.tar.gz
SITES.wallet-engine-0.0.7.tar.gz= -https://github.com/i582/wallet-engine/archive/${GITHUB_TAG}.tar.gz
WRKSRC= ${WRKDIR}/wallet-engine-${GITHUB_TAG}
HOMEPAGE= https://github.com/i582/wallet-engine
COMMENT= UniFFI C++ bindings generator for host build tools
LICENSE= mpl-2.0 AND mit AND apache-2.0 AND unicode-v3
USE_LANGUAGES= c c++
USE_TOOLS+= bsdtar
RUST_REQ= 1.99.1
EMBER_CARGO_PATCH_SET= yes
CARGO_WRKSRC= ${WRKSRC}/bindgen/cpp/bindgen
CARGO_ARGS= build --release --locked ${DEFAULT_CARGO_ARGS}
CARGO_INSTALL_ARGS= install --path . --locked --no-track --root ${DESTDIR}${PREFIX} --target-dir ${EMBER_CARGO_OUTPUT} ${DEFAULT_CARGO_ARGS}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} share/licenses/uniffi-bindgen-cpp -type f -print | ${SORT};
INSTALLATION_DIRS= bin share/licenses/uniffi-bindgen-cpp

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+= "uniffi-bindgen-cpp executes on the build host; build with native host MAKECONF"
.endif

post-extract:
	${CP} ${FILESDIR}/Cargo.lock ${WRKSRC}/bindgen/cpp/Cargo.lock
	${MKDIR} ${WRKDIR}/crates
	${LN} -s ${CARGO_VENDOR_DIR}/windows-sys-0.61.2 ${WRKDIR}/crates/windows-sys-0.61.2
	${LN} -s ${CARGO_VENDOR_DIR}/scroll_derive-0.12.1 ${WRKDIR}/crates/scroll_derive-0.12.1
	${LN} -s ${CARGO_VENDOR_DIR}/uniffi_internal_macros-0.32.2 ${WRKDIR}/crates/uniffi_internal_macros-0.32.2

do-install:
	cd ${CARGO_WRKSRC} && ${SETENV} ${MAKE_ENV} ${CARGO} ${CARGO_INSTALL_ARGS}
	${INSTALL_DATA} ${WRKSRC}/LICENSE-APACHE ${WRKSRC}/LICENSE-MIT ${DESTDIR}${PREFIX}/share/licenses/uniffi-bindgen-cpp/
	${INSTALL_DATA} ${WRKSRC}/bindgen/cpp/LICENSE ${DESTDIR}${PREFIX}/share/licenses/uniffi-bindgen-cpp/generator-MPL-2.0
	${MKDIR} ${DESTDIR}${PREFIX}/share/licenses/uniffi-bindgen-cpp/crates
	cd ${CARGO_VENDOR_DIR} && ${FIND} . -type f \( -iname 'license*' -o -iname 'licence*' -o -iname 'copying*' -o -iname 'notice*' -o -name Cargo.toml \) -print | ${TOOLBASE}/bin/bsdtar -cf - -T - | (cd ${DESTDIR}${PREFIX}/share/licenses/uniffi-bindgen-cpp/crates && ${TOOLBASE}/bin/bsdtar -xf -)

.include "cargo-depends.mk"
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../mk/bsd.pkg.mk"
