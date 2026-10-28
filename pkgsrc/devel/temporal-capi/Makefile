# $NetBSD$
DISTNAME= temporal_capi-0.2.6
PKGNAME= temporal-capi-0.2.6
CATEGORIES= devel
MASTER_SITES= https://static.crates.io/crates/temporal_capi/
EXTRACT_SUFX= .crate
HOMEPAGE= https://github.com/boa-dev/temporal
COMMENT= Shared C and C++ bindings for ECMAScript Temporal
LICENSE= mit AND apache-2.0 AND unicode-v3
USE_LANGUAGES= c c++
USE_TOOLS+= bsdtar
RUST_REQ= 1.99.1
CARGO_WRKSRC= ${WRKSRC}
CARGO_ARGS= build --release --locked --features zoneinfo64,compiled_data ${DEFAULT_CARGO_ARGS}

.include "../../mk/bsd.prefs.mk"
.if ${MACHINE_ARCH} == "aarch64"
_TEMPORAL_ARCH= aarch64
.elif ${MACHINE_ARCH} == "x86_64"
_TEMPORAL_ARCH= x86_64
.elif ${MACHINE_ARCH} == "i386"
_TEMPORAL_ARCH= i686
.elif ${MACHINE_ARCH} == "riscv64"
_TEMPORAL_ARCH= riscv64gc
.elif ${MACHINE_ARCH} == "powerpc"
_TEMPORAL_ARCH= powerpc
.elif ${MACHINE_ARCH} == "sparc64"
_TEMPORAL_ARCH= sparc64
.elif ${MACHINE_ARCH} == "mipsel"
_TEMPORAL_ARCH= mipsel
.endif
.if ${MACHINE_ARCH} == "earmv6hf" && ${OPSYS} == "NetBSD"
_TEMPORAL_TARGET= armv6-unknown-netbsd-eabihf
.elif ${MACHINE_ARCH} == "earmv7hf" && ${OPSYS} == "NetBSD"
_TEMPORAL_TARGET= armv7-unknown-netbsd-eabihf
.elif defined(_TEMPORAL_ARCH)
.  if ${OPSYS} == "Darwin"
_TEMPORAL_TARGET= ${_TEMPORAL_ARCH}-apple-darwin
.  elif ${OPSYS} == "NetBSD" || ${OPSYS} == "FreeBSD"
_TEMPORAL_TARGET= ${_TEMPORAL_ARCH}-unknown-${LOWER_OPSYS}
.  elif ${OPSYS} == "Linux"
.    if !empty(MACHINE_GNU_PLATFORM:M*musl*)
_TEMPORAL_TARGET= ${_TEMPORAL_ARCH}-unknown-linux-musl
.    else
_TEMPORAL_TARGET= ${_TEMPORAL_ARCH}-unknown-linux-gnu
.    endif
.  endif
.endif
EMBER_CARGO_TARGET?= ${_TEMPORAL_TARGET:U}
.if empty(EMBER_CARGO_TARGET)
.  error "Set EMBER_CARGO_TARGET to a supported Rust target triple"
.endif
.if ${OPSYS} == "Darwin"
_TEMPORAL_LIB= libtemporal_capi.dylib
.else
_TEMPORAL_LIB= libtemporal_capi.so
.endif
PLIST_SUBST+= TEMPORAL_LIB=${_TEMPORAL_LIB}
INSTALLATION_DIRS= lib lib/pkgconfig include include/temporal_capi share/licenses/temporal-capi
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} share/licenses/temporal-capi -type f -print | ${SORT};

post-extract:
	${CP} ${FILESDIR}/Cargo.lock ${WRKSRC}/Cargo.lock

do-install:
	${INSTALL_LIB} ${EMBER_CARGO_OUTPUT}/${EMBER_CARGO_TARGET}/release/${_TEMPORAL_LIB} ${DESTDIR}${PREFIX}/lib/${_TEMPORAL_LIB}
.if ${OPSYS} == "Darwin"
	${EMBERBSD_DARWIN_INSTALL_NAME_TOOL:U${TOOLBASE}/bin/llvm-install-name-tool} -id ${PREFIX}/lib/${_TEMPORAL_LIB} ${DESTDIR}${PREFIX}/lib/${_TEMPORAL_LIB}
.endif
	cd ${WRKSRC}/bindings/cpp && ${TOOLBASE}/bin/bsdtar -cf - temporal_rs | (cd ${DESTDIR}${PREFIX}/include && ${TOOLBASE}/bin/bsdtar -xf -)
	cd ${WRKSRC}/bindings/c && ${TOOLBASE}/bin/bsdtar -cf - . | (cd ${DESTDIR}${PREFIX}/include/temporal_capi && ${TOOLBASE}/bin/bsdtar -xf -)
	${SED} -e 's,@PREFIX@,${PREFIX},g' ${FILESDIR}/temporal_capi.pc.in > ${DESTDIR}${PREFIX}/lib/pkgconfig/temporal_capi.pc
	${INSTALL_DATA} ${WRKSRC}/LICENSE-MIT ${WRKSRC}/LICENSE-Apache ${DESTDIR}${PREFIX}/share/licenses/temporal-capi
	${TOOL_PYTHONBIN} -B -I -S ${FILESDIR}/install-notices.py --lock ${WRKSRC}/Cargo.lock --vendor ${CARGO_VENDOR_DIR} --output ${DESTDIR}${PREFIX}/share/licenses/temporal-capi/crates

.include "cargo-depends.mk"
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../mk/bsd.pkg.mk"
