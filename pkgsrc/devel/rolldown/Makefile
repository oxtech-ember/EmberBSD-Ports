# $NetBSD$
# Origin: EmberBSD (AI-assisted); upstream Rolldown with a source-built N-API binding.

DISTNAME=	rolldown-1.3.3
CATEGORIES=	devel
ROLLDOWN_REVISION=	8a576d2fb72eab5374059b5cb216ee35412ca019
DISTFILES=	rolldown-${ROLLDOWN_REVISION}.tar.gz ${DISTNAME}.tgz
SITES.rolldown-${ROLLDOWN_REVISION}.tar.gz=	-https://github.com/rolldown/rolldown/archive/${ROLLDOWN_REVISION}.tar.gz
SITES.${DISTNAME}.tgz=	https://registry.npmjs.org/rolldown/-/
WRKSRC=		${WRKDIR}/rolldown-${ROLLDOWN_REVISION}
EXTRACT_DIR.${DISTNAME}.tgz=	${WRKSRC}/npm
REPLACE_NODEJS=	npm/package/bin/cli.mjs

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://rolldown.rs/
COMMENT=	JavaScript bundler with source-built native Rust core
LICENSE=	mit AND apache-2.0 AND isc AND zlib AND mpl-2.0 AND modified-bsd AND \
		2-clause-bsd AND boost-license AND cc0-1.0-universal AND unicode-v3

DEPENDS+=	node-oxc-project-types-0.159.0{,nb[0-9]*}:../../devel/node-oxc-project-types
DEPENDS+=	node-rolldown-pluginutils>=1.0.0<2:../../devel/node-rolldown-pluginutils
DEPENDS+=	nodejs>=26.12.1<27:../../lang/nodejs

USE_LANGUAGES=	c c++
USE_TOOLS+=	pax pkg-config
RUST_REQ=	1.100.0
CARGO_WRKSRC=	${WRKSRC}
CARGO_ARGS=	build --release --locked --package rolldown_binding ${DEFAULT_CARGO_ARGS}
MACHO_USE_LOAD_COMMANDS=	yes

.include "../../mk/bsd.prefs.mk"

.if ${MACHINE_ARCH} == "aarch64"
_ROLLDOWN_RUST_ARCH=	aarch64
_ROLLDOWN_NODE_ARCH=	arm64
.elif ${MACHINE_ARCH} == "x86_64"
_ROLLDOWN_RUST_ARCH=	x86_64
_ROLLDOWN_NODE_ARCH=	x64
.endif
.if defined(_ROLLDOWN_RUST_ARCH)
.  if ${OPSYS} == "Darwin"
_ROLLDOWN_RUST_TARGET=	${_ROLLDOWN_RUST_ARCH}-apple-darwin
_ROLLDOWN_NAPI_BASE=	darwin-${_ROLLDOWN_NODE_ARCH}
.  elif ${OPSYS} == "FreeBSD"
_ROLLDOWN_RUST_TARGET=	${_ROLLDOWN_RUST_ARCH}-unknown-freebsd
_ROLLDOWN_NAPI_BASE=	freebsd-${_ROLLDOWN_NODE_ARCH}
.  endif
.endif
EMBER_CARGO_TARGET?=	${_ROLLDOWN_RUST_TARGET:U}
ROLLDOWN_NAPI_BASE?=	${_ROLLDOWN_NAPI_BASE:U}
.if ${OPSYS} == "Darwin"
ROLLDOWN_DYLIB_SUFFIX=	dylib
.else
ROLLDOWN_DYLIB_SUFFIX=	so
.endif
PLIST_SUBST+=	ROLLDOWN_NAPI_BASE=${ROLLDOWN_NAPI_BASE:Q}

.if ${OPSYS} != "Darwin"
RUSTFLAGS+=	-C link-arg=-Wl,-rpath,${PREFIX}/lib
.endif
RUSTFLAGS+=	--remap-path-prefix=${WRKDIR}=.
EMBER_CARGO_CONFIGURE_ARGS+=	--build-script-overrides ${WRKDIR:Q}/mimalloc-links.toml

EMBER_CARGO_INSTALLED_CDYLIB=	lib/node_modules/rolldown/dist/shared/rolldown-binding.${ROLLDOWN_NAPI_BASE}.node
INSTALLATION_DIRS=	lib/node_modules/rolldown share/licenses/rolldown
GENERATE_PLIST+=	cd ${DESTDIR}${PREFIX}; ${FIND} share/licenses/rolldown -type f -print | ${SORT};

ember-cargo-configure: ember-mimalloc-consumer-options rolldown-source-inputs
.PHONY: rolldown-source-inputs
rolldown-source-inputs:
	${RUN} ${TOOL_PYTHONBIN} -B -I -S ${FILESDIR:Q}/prepare.py \
	    --source ${WRKSRC:Q} --version ${PKGVERSION_NOREV:Q} \
	    --rust-target=${EMBER_CARGO_TARGET:Q} --napi-base=${ROLLDOWN_NAPI_BASE:Q} \
	    --mimalloc-libdir ${BUILDLINK_DIR:Q}/lib --mimalloc-library ${MIMALLOC_EMBED_LIBRARY:Q} \
	    --output ${WRKDIR:Q}/mimalloc-links.toml

do-test:
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${FAIL_MSG} "Run the Rolldown native-addon consumer on the selected target; do not execute target Node on the host"
.else
	${SETENV} ${TEST_ENV} NODE_PATH=${PREFIX}/lib/node_modules ${PREFIX}/bin/node ${FILESDIR}/smoke.mjs \
	    ${WRKSRC}/npm/package \
	    ${EMBER_CARGO_OUTPUT}/${EMBER_CARGO_TARGET}/release/librolldown_binding.${ROLLDOWN_DYLIB_SUFFIX} \
	    ${ROLLDOWN_NAPI_BASE} ${WRKDIR}/node-smoke
.endif

do-install:
	cd ${WRKSRC}/npm/package && ${PAX} -rw . ${DESTDIR}${PREFIX}/lib/node_modules/rolldown
	${INSTALL_LIB} ${EMBER_CARGO_OUTPUT}/${EMBER_CARGO_TARGET}/release/librolldown_binding.${ROLLDOWN_DYLIB_SUFFIX} \
	    ${DESTDIR:Q}${PREFIX:Q}/${EMBER_CARGO_INSTALLED_CDYLIB:Q}
.if ${OPSYS} == "Darwin"
	${TOOLBASE:Q}/bin/llvm-install-name-tool \
	    -change @rpath/libmimalloc-embed.3.dylib \
	    '@loader_path/../../../../libmimalloc-embed.3.dylib' \
	    ${DESTDIR:Q}${PREFIX:Q}/${EMBER_CARGO_INSTALLED_CDYLIB:Q}
.endif
	${TOOL_PYTHONBIN} -B -I -S ${PKGSRCDIR:Q}/devel/rollup/files/install-notices.py \
	    --lock ${CARGO_WRKSRC:Q}/Cargo.lock --vendor ${CARGO_VENDOR_DIR:Q} \
	    --output ${DESTDIR:Q}${PREFIX:Q}/share/licenses/rolldown \
	    --license-root ${PKGSRCDIR:Q}/licenses

.include "cargo-depends.mk"
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../devel/mimalloc/embedding.mk"
.include "../../lang/nodejs/application.mk"
.include "../../mk/bsd.pkg.mk"
