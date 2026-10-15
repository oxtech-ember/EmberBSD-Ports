# SPDX-License-Identifier: BSD-2-Clause
# Host Cargo and target compilers are separate providers.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if ${CROSS_MACHINE_ARCH:U} == "aarch64"
_EMBER_CSS_RUST_TARGET= aarch64-unknown-netbsd
_EMBER_CSS_GNU_TRIPLET= aarch64--netbsd
_EMBER_CSS_STD_PACKAGE= rust-std-aarch64-netbsd
.elif ${CROSS_MACHINE_ARCH:U} == "x86_64"
_EMBER_CSS_RUST_TARGET= x86_64-unknown-netbsd
_EMBER_CSS_GNU_TRIPLET= x86_64--netbsd
_EMBER_CSS_STD_PACKAGE= rust-std-x86_64-netbsd
.else
PKG_FAIL_REASON+= "cxx-rust-cssparser supports only aarch64 and x86_64 cross targets"
.endif
RUST_TARGET= ${_EMBER_CSS_RUST_TARGET:Uunsupported}
.if ${CROSS_OPSYS:U} != "NetBSD" || empty(CROSS_OS_VERSION:M11.*) || \
    "${MACHINE_ARCH:U}" != "${CROSS_MACHINE_ARCH:U}" || \
    "${MACHINE_GNU_PLATFORM:U}" != "${_EMBER_CSS_GNU_TRIPLET:U}" || \
    "${RUST_TARGET}" != "${_EMBER_CSS_RUST_TARGET:U}"
PKG_FAIL_REASON+= "cxx-rust-cssparser requires matching NetBSD 11 Rust and GCC16 targets"
.endif
TOOL_DEPENDS+= rust-bin-1.99.0{,nb[0-9]*}:../../lang/rust-bin
.if defined(_EMBER_CSS_STD_PACKAGE)
TOOL_DEPENDS+= ${_EMBER_CSS_STD_PACKAGE}-1.99.0{,nb[0-9]*}:../../lang/${_EMBER_CSS_STD_PACKAGE}
.endif
_EMBER_CSS_HOST_CC= ${EMBERBSD_CROSS_BUILD_CC:U/usr/bin/cc}
_EMBER_CSS_HOST_CXX= ${EMBERBSD_CROSS_BUILD_CXX:U/usr/bin/c++}
.for host_driver in _EMBER_CSS_HOST_CC _EMBER_CSS_HOST_CXX
.if empty(${host_driver}:M/*) || !exists(${${host_driver}})
PKG_FAIL_REASON+= "cxx-rust-cssparser requires absolute native build compilers"
.endif
.endfor
RUST_OUT= ${WRKDIR}/rust-out
BRIDGE_A= ${WRKDIR}/libcxx-rust-cssparser-impl-bridge.a
BRIDGE_INC= ${WRKDIR}/bridge-include
_EMBER_CSS_RUST_KEY= ${RUST_TARGET:tu:S/-/_/g}
_EMBER_CSS_CC_KEY= ${RUST_TARGET:S/-/_/g}
_EMBER_CSS_CC= ${WRKDIR}/.cwrapper/bin/${_EMBER_CSS_GNU_TRIPLET}-gcc
_EMBER_CSS_CXX= ${WRKDIR}/.cwrapper/bin/${_EMBER_CSS_GNU_TRIPLET}-g++
CARGO_ENV= CARGO_HOME=${WRKDIR}/cargo-home CARGO_TARGET_DIR=${RUST_OUT}
CARGO_ENV+= RUSTC=${EMBERBSD_CROSS_HOST_PREFIX}/bin/rustc CARGO_NET_OFFLINE=true
CARGO_ENV+= CARGO_TARGET_${_EMBER_CSS_RUST_KEY}_LINKER=${_EMBER_CSS_CC}
CARGO_ENV+= CC_${_EMBER_CSS_CC_KEY}=${_EMBER_CSS_CC}
CARGO_ENV+= CXX_${_EMBER_CSS_CC_KEY}=${_EMBER_CSS_CXX}
CARGO_ENV+= AR_${_EMBER_CSS_CC_KEY}=${AR}
CARGO_ENV+= CC=${_EMBER_CSS_HOST_CC} CXX=${_EMBER_CSS_HOST_CXX}
CARGO_ENV+= HOST_CC=${_EMBER_CSS_HOST_CC} HOST_CXX=${_EMBER_CSS_HOST_CXX}

pre-configure:
	@set -e; \
	rust_host=$$(${SH} ${FILESDIR:Q}/verify-cross-inputs.sh \
		${EMBERBSD_CROSS_HOST_PREFIX:Q} ${RUST_TARGET:Q} ${_EMBER_CSS_GNU_TRIPLET:Q} \
		${WRKDIR:Q}/.cwrapper/bin ${WRKDIR:Q}/target-std-check.rmeta); \
	host_key=$$(printf '%s' "$$rust_host" | tr '[:lower:]-' '[:upper:]_'); \
	cd ${WRKSRC:Q}/rust; \
	mkdir -p .cargo; \
	printf '[source.crates-io]\nreplace-with = "vendored-sources"\n\n[source.vendored-sources]\ndirectory = "vendor"\n' > .cargo/config.toml; \
	${SETENV} ${CARGO_ENV} "CARGO_TARGET_$${host_key}_LINKER=${_EMBER_CSS_HOST_CC}" \
		${EMBERBSD_CROSS_HOST_PREFIX:Q}/bin/cargo build --release --target ${RUST_TARGET:Q} --offline; \
	bdir="$$(${FIND} ${RUST_OUT}/${RUST_TARGET}/release/build -path '*out/cxxbridge/sources' -type d | head -1 | sed 's|/out/cxxbridge/sources||')"; \
	[ -n "$$bdir" ] || { echo 'no cxxbridge output found' >&2; exit 1; }; \
	${RM} -rf ${BRIDGE_INC}; \
	${CP} -R $$bdir/out/cxxbridge/include ${BRIDGE_INC}; \
	${_EMBER_CSS_CXX} -std=c++20 -fPIC -O2 \
		-Wno-maybe-uninitialized -I${BRIDGE_INC} \
		-c $$bdir/out/cxxbridge/sources/cxx-rust-cssparser-impl/src/ffi.rs.cc \
		-o ${WRKDIR}/bridge.o; \
	${AR} qc ${BRIDGE_A} ${WRKDIR}/bridge.o

CMAKE_CONFIGURE_ARGS+= -DEMBER_RUST_LIB=${RUST_OUT}/${RUST_TARGET}/release/libcxx_rust_cssparser_impl.a
CMAKE_CONFIGURE_ARGS+= -DEMBER_BRIDGE_LIB=${BRIDGE_A}
CMAKE_CONFIGURE_ARGS+= -DEMBER_BRIDGE_INCLUDE=${BRIDGE_INC}
.endif
