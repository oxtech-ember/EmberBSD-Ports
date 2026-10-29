# $NetBSD: Makefile,v 1.6 2025/09/01 06:12:29 adam Exp $

DISTNAME=	rust-bindgen-0.73.2
PKGREVISION=	2
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=rust-lang/}
GITHUB_TAG=	refs/tags/v${PKGVERSION_NOREV}
WRKSRC=		${WRKDIR}/${DISTNAME}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/rust-lang/rust-bindgen
COMMENT=	Automatically generate Rust FFI bindings to C and C++ libraries
LICENSE=	modified-bsd AND mit AND apache-2.0 AND isc AND unicode-v3

# The CLI loads libclang at runtime and uses rustfmt by default.
DEPENDS+=	rust-bin>=1.99.1:../../lang/rust-bin
USE_LANGUAGES=	c c++
USE_TOOLS+=	pax
RUST_REQ=	1.99.1
EMBER_CARGO_PATCH_SET=	yes
CARGO_ARGS=	build --release --locked --package bindgen-cli ${DEFAULT_CARGO_ARGS}
CARGO_INSTALL_ARGS= install --path bindgen-cli --locked --no-track \
		--root ${DESTDIR}${PREFIX} --target-dir ${EMBER_CARGO_OUTPUT} ${DEFAULT_CARGO_ARGS}
RUSTFLAGS+=	--remap-path-prefix=${WRKDIR}=.

INSTALLATION_DIRS= bin share/licenses/rust-bindgen
GENERATE_PLIST+=	cd ${DESTDIR}${PREFIX}; ${FIND} share/licenses/rust-bindgen -type f -print | ${SORT};

.include "../../mk/bsd.prefs.mk"

.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 3
DEPENDS+= clang>=23.1.4nb12:../../lang/clang
.else
DEPENDS+= clang>=23.1.4:../../lang/clang
.endif

do-test:
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${FAIL_MSG} "Run the bindgen CLI tests on the selected target; do not execute target binaries on the host"
.else
	${SETENV} ${TEST_ENV} ${MAKE_ENV} LIBCLANG_PATH=${TOOLBASE}/lib \
	    CLANG_PATH=${TOOLBASE}/bin/clang RUSTFMT=${TOOLBASE}/bin/rustfmt \
	    ${TOOL_PYTHONBIN} -B -I -S ${FILESDIR}/smoke.py \
	    --config ${EMBER_CARGO_CONFIG} --output ${WRKDIR}/bindgen-smoke \
	    --rustc ${TOOLBASE}/bin/rustc --cc=${CC:Q} --cppflags=${CPPFLAGS:Q}
.endif

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/rust-bindgen
	${MKDIR} ${DESTDIR}${PREFIX}/share/licenses/rust-bindgen/crates
	cd ${CARGO_VENDOR_DIR} && ${FIND} . -type f \
	    \( -iname 'license*' -o -iname 'licence*' -o -iname 'copying*' \
	    -o -iname 'notice*' -o -name Cargo.toml \) -print | \
	    ${PAX} -rw ${DESTDIR}${PREFIX}/share/licenses/rust-bindgen/crates

.include "cargo-depends.mk"
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../mk/bsd.pkg.mk"
