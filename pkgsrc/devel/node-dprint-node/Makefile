# Origin: EmberBSD contributors (AI-assisted); source-built Node formatter.
DISTNAME= dprint-node-1.0.8
PKGREVISION= 1
CATEGORIES= devel
DPRINT_NODE_REV= f21bd38ae8e3239ffe07c941c938349eebdb2c5e
DPRINT_TS_REV= 98525274ee276fb61709c77f791b212a48c59dd6
DISTFILES= dprint-node-${DPRINT_NODE_REV}.tar.gz dprint-plugin-typescript-${DPRINT_TS_REV}.tar.gz
SITES.dprint-node-${DPRINT_NODE_REV}.tar.gz= -https://github.com/devongovett/dprint-node/archive/${DPRINT_NODE_REV}.tar.gz
SITES.dprint-plugin-typescript-${DPRINT_TS_REV}.tar.gz= -https://github.com/dprint/dprint-plugin-typescript/archive/${DPRINT_TS_REV}.tar.gz
WRKSRC= ${WRKDIR}/dprint-node-${DPRINT_NODE_REV}
TS_SOURCE= ${WRKDIR}/dprint-plugin-typescript-${DPRINT_TS_REV}
HOMEPAGE= https://github.com/devongovett/dprint-node
COMMENT= Source-built N-API TypeScript and JavaScript formatter
LICENSE= mit AND apache-2.0 AND modified-bsd AND isc AND unicode-v3 AND 0-clause-bsd
DEPENDS+= nodejs>=26.12.1<27:../../lang/nodejs
USE_LANGUAGES= c c++
USE_TOOLS+= pax
RUST_REQ= 1.99.1
EMBER_CARGO_PATCH_SET= yes
CARGO_ARGS= build --release --locked ${DEFAULT_CARGO_ARGS}
MACHO_USE_LOAD_COMMANDS= yes
RUSTFLAGS+= --remap-path-prefix=${WRKDIR}=.
INSTALLATION_DIRS= lib/node_modules/dprint-node share/licenses/dprint-node
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} share/licenses/dprint-node -type f -print | ${SORT};

.include "../../mk/bsd.prefs.mk"
.if ${MACHINE_ARCH} == "aarch64"
_DPRINT_ARCH= aarch64
.elif ${MACHINE_ARCH} == "x86_64"
_DPRINT_ARCH= x86_64
.endif
.if defined(_DPRINT_ARCH)
.  if ${OPSYS} == "Darwin"
_DPRINT_TARGET= ${_DPRINT_ARCH}-apple-darwin
.  elif ${OPSYS} == "NetBSD" || ${OPSYS} == "FreeBSD"
_DPRINT_TARGET= ${_DPRINT_ARCH}-unknown-${LOWER_OPSYS}
.  elif ${OPSYS} == "Linux"
.    if !empty(MACHINE_GNU_PLATFORM:M*musl*)
_DPRINT_TARGET= ${_DPRINT_ARCH}-unknown-linux-musl
.    else
_DPRINT_TARGET= ${_DPRINT_ARCH}-unknown-linux-gnu
.    endif
.  endif
.endif
EMBER_CARGO_TARGET?= ${_DPRINT_TARGET:U}
.if ${OPSYS} == "Darwin"
_DPRINT_SUFFIX= dylib
.else
_DPRINT_SUFFIX= so
.endif

post-extract:
	${RM} -f ${WRKSRC}/.cargo/config.toml
post-patch:
	${EMBER_CARGO_PREFIX}/bin/gpatch --batch -F 0 -p1 -d ${TS_SOURCE:Q} -i ${FILESDIR:Q}/typescript-swc29.patch

do-test:
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${FAIL_MSG} "Run the formatter consumer test on the selected target Node"
.else
	${SETENV} ${TEST_ENV} ${PREFIX}/bin/node ${FILESDIR}/smoke.cjs ${EMBER_CARGO_OUTPUT}/${EMBER_CARGO_TARGET}/release/libdprint_node.${_DPRINT_SUFFIX} ${WRKDIR}/node-smoke
.endif

do-install:
	${INSTALL_DATA} ${WRKSRC}/index.js ${WRKSRC}/package.json ${WRKSRC}/index.d.ts ${WRKSRC}/options.d.ts ${DESTDIR}${PREFIX}/lib/node_modules/dprint-node
	${INSTALL_LIB} ${EMBER_CARGO_OUTPUT}/${EMBER_CARGO_TARGET}/release/libdprint_node.${_DPRINT_SUFFIX} ${DESTDIR}${PREFIX}/lib/node_modules/dprint-node/dprint-node.node
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/dprint-node/LICENSE
	${INSTALL_DATA} ${TS_SOURCE}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/dprint-node/LICENSE.typescript
	${MKDIR} ${DESTDIR}${PREFIX}/share/licenses/dprint-node/crates
	cd ${CARGO_VENDOR_DIR} && ${FIND} . -type f \( -iname 'license*' -o -iname 'licence*' -o -iname 'copying*' -o -iname 'notice*' -o -name Cargo.toml \) -print | ${PAX} -rw ${DESTDIR}${PREFIX}/share/licenses/dprint-node/crates

.include "cargo-depends.mk"
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../lang/nodejs/application.mk"
.include "../../mk/bsd.pkg.mk"
