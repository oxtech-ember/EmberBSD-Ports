# $NetBSD$

DISTNAME=	rollup-4.65.1
PKGREVISION=	2
CATEGORIES=	devel
ROLLUP_REVISION=	7879c65994dd591d287b177b8d0b88d7d76c2a49
DISTFILES=	rollup-${ROLLUP_REVISION}.tar.gz ${DISTNAME}.tgz
SITES.rollup-${ROLLUP_REVISION}.tar.gz=	-https://github.com/rollup/rollup/archive/${ROLLUP_REVISION}.tar.gz
SITES.${DISTNAME}.tgz=	https://registry.npmjs.org/rollup/-/
WRKSRC=		${WRKDIR}/rollup-${ROLLUP_REVISION}
EXTRACT_DIR.${DISTNAME}.tgz=	${WRKSRC}/npm

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://rollupjs.org/
COMMENT=	JavaScript module bundler with source-built native parser
# Rust workspace/crates and bundled JS notices retain their original expressions.
LICENSE=	mit AND apache-2.0 AND boost-license AND unicode-v3 AND zlib AND \
		modified-bsd AND isc AND 0-clause-bsd

DEPENDS+=	node-types-estree>=1.0.9:../../devel/node-types-estree
DEPENDS+=	nodejs>=24.22.1<25:../../lang/nodejs24

USE_LANGUAGES=	c c++
USE_TOOLS+=	pax pkg-config
RUST_REQ=	1.99.1
CARGO_WRKSRC=	${WRKSRC}/rust
EMBER_CARGO_PATCH_SET=	yes
CARGO_ARGS=	build --release --locked --package bindings_napi ${DEFAULT_CARGO_ARGS}
REPLACE_NODEJS=	npm/package/dist/bin/rollup
MACHO_USE_LOAD_COMMANDS=	yes

.include "../../mk/bsd.prefs.mk"

# These defaults cover the current native Darwin and EmberBSD tool profiles.
# Other upstream platforms can supply the matching Rust target and N-API base.
.if ${MACHINE_ARCH} == "aarch64"
_ROLLUP_RUST_ARCH=	aarch64
_ROLLUP_NODE_ARCH=	arm64
.elif ${MACHINE_ARCH} == "x86_64"
_ROLLUP_RUST_ARCH=	x86_64
_ROLLUP_NODE_ARCH=	x64
.endif
.if defined(_ROLLUP_RUST_ARCH)
.  if ${OPSYS} == "Darwin"
_ROLLUP_RUST_TARGET=	${_ROLLUP_RUST_ARCH}-apple-darwin
_ROLLUP_NAPI_BASE=	darwin-${_ROLLUP_NODE_ARCH}
.  elif ${OPSYS} == "NetBSD" || ${OPSYS} == "FreeBSD"
_ROLLUP_RUST_TARGET=	${_ROLLUP_RUST_ARCH}-unknown-${LOWER_OPSYS}
_ROLLUP_NAPI_BASE=	${LOWER_OPSYS}-${_ROLLUP_NODE_ARCH}
.  elif ${OPSYS} == "Linux"
.    if !empty(MACHINE_GNU_PLATFORM:M*musl*)
_ROLLUP_LIBC=	musl
.    else
_ROLLUP_LIBC=	gnu
.    endif
_ROLLUP_RUST_TARGET=	${_ROLLUP_RUST_ARCH}-unknown-linux-${_ROLLUP_LIBC}
_ROLLUP_NAPI_BASE=	linux-${_ROLLUP_NODE_ARCH}-${_ROLLUP_LIBC}
.  endif
.endif
EMBER_CARGO_TARGET?=	${_ROLLUP_RUST_TARGET:U}
ROLLUP_NAPI_BASE?=	${_ROLLUP_NAPI_BASE:U}
.if ${OPSYS} == "Darwin"
ROLLUP_DYLIB_SUFFIX=	dylib
.else
ROLLUP_DYLIB_SUFFIX=	so
.endif
PLIST_SUBST+=	ROLLUP_NAPI_BASE=${ROLLUP_NAPI_BASE:Q}

# The native addon uses mi_* and must not interpose the Node process allocator.
MIMALLOC_REQUIRE_OVERRIDE=	no
.if ${OPSYS} == "Linux" || ${OPSYS} == "FreeBSD" || ${OPSYS} == "NetBSD"
MIMALLOC_REQUIRE_DYNAMIC_TLS=	yes
.endif
.if ${MACHINE_ARCH} == "aarch64" && ${OPSYS} != "Darwin"
MIMALLOC_REQUIRE_GENERIC_ARCH=	yes
.endif
RUSTFLAGS+=	-C link-arg=-Wl,-rpath,${PREFIX}/lib
RUSTFLAGS+=	--remap-path-prefix=${WRKDIR}=.
EMBER_CARGO_CONFIGURE_ARGS+=	--build-script-overrides ${WRKDIR:Q}/mimalloc-links.toml

INSTALLATION_DIRS=	bin lib/node_modules/rollup share/licenses/rollup
GENERATE_PLIST+=	cd ${DESTDIR}${PREFIX}; ${FIND} share/licenses/rollup -type f -print | ${SORT};

ember-cargo-configure: ember-mimalloc-consumer-options rollup-source-inputs
.PHONY: rollup-source-inputs
rollup-source-inputs:
	${RUN} ${TOOL_PYTHONBIN} -B -I -S ${FILESDIR:Q}/prepare.py \
	    --source ${WRKSRC:Q} --version ${PKGVERSION_NOREV:Q} \
	    --rust-target=${EMBER_CARGO_TARGET:Q} --napi-base=${ROLLUP_NAPI_BASE:Q} \
	    --mimalloc-libdir ${BUILDLINK_DIR:Q}/lib --output ${WRKDIR:Q}/mimalloc-links.toml

do-test:
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${FAIL_MSG} "Run the Rollup native-addon consumer on the selected target; do not execute target Node on the host"
.else
	${SETENV} ${TEST_ENV} NODE_PATH= ${PREFIX}/bin/node ${FILESDIR}/smoke.cjs \
	    ${WRKSRC}/npm/package \
	    ${EMBER_CARGO_OUTPUT}/${EMBER_CARGO_TARGET}/release/libbindings_napi.${ROLLUP_DYLIB_SUFFIX} \
	    ${ROLLUP_NAPI_BASE} ${WRKDIR}/node-smoke
.endif

do-install:
	cd ${WRKSRC}/npm/package && ${PAX} -rw . ${DESTDIR}${PREFIX}/lib/node_modules/rollup
	${RM} -f ${DESTDIR}${PREFIX}/lib/node_modules/rollup/dist/native.js.orig
	${INSTALL_SCRIPT} ${WRKSRC}/npm/package/dist/bin/rollup \
	    ${DESTDIR}${PREFIX}/lib/node_modules/rollup/dist/bin/rollup
	${INSTALL_LIB} ${EMBER_CARGO_OUTPUT}/${EMBER_CARGO_TARGET}/release/libbindings_napi.${ROLLUP_DYLIB_SUFFIX} \
	    ${DESTDIR}${PREFIX}/lib/node_modules/rollup/dist/rollup.${ROLLUP_NAPI_BASE}.node
	${LN} -sf ../lib/node_modules/rollup/dist/bin/rollup ${DESTDIR}${PREFIX}/bin/rollup
	${TOOL_PYTHONBIN} -B -I -S ${FILESDIR:Q}/install-notices.py \
	    --lock ${CARGO_WRKSRC:Q}/Cargo.lock --vendor ${CARGO_VENDOR_DIR:Q} \
	    --output ${DESTDIR:Q}${PREFIX:Q}/share/licenses/rollup \
	    --license-root ${PKGSRCDIR:Q}/licenses \
	    --extra-notices ${FILESDIR:Q}/licenses/origins.json

.include "cargo-depends.mk"
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../devel/mimalloc/buildlink3.mk"
.include "../../lang/nodejs/application.mk"
.include "../../mk/bsd.pkg.mk"
