# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Included only for cross builds, after
# the librsvg cross recipe in graphics/librsvg.
RUST_TYPE= native
TOOL_DEPENDS+= rust-bin-1.99.1{,nb[0-9]*}:../../lang/rust-bin
# Keep the Rust target, std package and binary tools on the selected target.
.if ${EMBERBSD_CROSS_TARGET:U} == "aarch64"
_EMBER_GLYCIN_RUST_TARGET= aarch64-unknown-netbsd
_EMBER_GLYCIN_STD_PACKAGE= rust-std-aarch64-netbsd
_EMBER_GLYCIN_TRIPLET= aarch64--netbsd
.elif ${EMBERBSD_CROSS_TARGET:U} == "amd64"
_EMBER_GLYCIN_RUST_TARGET= x86_64-unknown-netbsd
_EMBER_GLYCIN_STD_PACKAGE= rust-std-x86_64-netbsd
_EMBER_GLYCIN_TRIPLET= x86_64--netbsd
.else
PKG_FAIL_REASON+= "glycin requires a supported Rust cross target"
.endif
.if defined(_EMBER_GLYCIN_STD_PACKAGE)
TOOL_DEPENDS+= ${_EMBER_GLYCIN_STD_PACKAGE}-1.99.1{,nb[0-9]*}:../../lang/${_EMBER_GLYCIN_STD_PACKAGE}
.endif
_EMBER_GLYCIN_RUST_KEY= ${_EMBER_GLYCIN_RUST_TARGET:Uunsupported:tu:S/-/_/g}
_EMBER_GLYCIN_CC_KEY= ${_EMBER_GLYCIN_RUST_TARGET:Uunsupported:S/-/_/g}

# The upstream meson build reads the cargo target from this property.
MESON_CROSS_VARS+= rust_target
MESON_CROSS.rust_target= '${_EMBER_GLYCIN_RUST_TARGET:Uunsupported}'

# The installed-library step inspects target ELF, not Mach-O.
MESON_BINARIES+= nm strip
MESON_BINARY.nm= ${TOOLDIR}/bin/${_EMBER_GLYCIN_TRIPLET:Uunsupported}-nm
MESON_BINARY.strip= ${TOOLDIR}/bin/${_EMBER_GLYCIN_TRIPLET:Uunsupported}-strip

# pkgsrc's native Rust mode avoids selecting a target compiler package.
TOOLS_CREATE+= cargo rustc
.for _rust_tool in cargo rustc
TOOLS_PATH.${_rust_tool}= ${TOOLBASE}/bin/${_rust_tool}
.endfor
MAKE_ENV+= RUSTC=${TOOLBASE}/bin/rustc
MAKE_ENV+= CARGO_NET_OFFLINE=true CARGO_BUILD_JOBS=${MAKE_JOBS:U1}
MAKE_ENV+= CARGO_TARGET_${_EMBER_GLYCIN_RUST_KEY}_LINKER=${WRAPPER_BINDIR}/cc
.if exists(${TOOLBASE}/bin/rustc)
_EMBER_GLYCIN_AWK= ${EMBERBSD_NATIVE_AWK:U${TOOLBASE}/bin/nawk}
_EMBER_GLYCIN_RUST_HOST!= ${TOOLBASE:Q}/bin/rustc -vV | ${_EMBER_GLYCIN_AWK:Q} \
    '/^release: / {release=$$2} /^commit-hash: / {commit=$$2} /^host: / {host=$$2} \
    END {if (release == "1.99.1" && commit == "58cf8f9c35b355199727627d07ae34a4e2846d67") print host; else exit 1}'
.if empty(_EMBER_GLYCIN_RUST_HOST) || !empty(_EMBER_GLYCIN_RUST_HOST:C/[A-Za-z0-9_-]//g)
PKG_FAIL_REASON+= "glycin requires the shared official native Rust 1.99.1 provider"
.else
_EMBER_GLYCIN_HOST_KEY= ${_EMBER_GLYCIN_RUST_HOST:tu:S/-/_/g}
MAKE_ENV+= CARGO_TARGET_${_EMBER_GLYCIN_HOST_KEY}_LINKER=${EMBERBSD_CROSS_BUILD_CC}
.endif
.endif
MAKE_ENV+= HOST_CC=${EMBERBSD_CROSS_BUILD_CC} HOST_CXX=${EMBERBSD_CROSS_BUILD_CXX}
MAKE_ENV+= HOST_AR=${EMBERBSD_CROSS_BUILD_AR}
MAKE_ENV+= HOST_CFLAGS= HOST_CXXFLAGS=
MAKE_ENV+= CC_${_EMBER_GLYCIN_CC_KEY}=${WRAPPER_BINDIR}/cc
MAKE_ENV+= CXX_${_EMBER_GLYCIN_CC_KEY}=${WRAPPER_BINDIR}/c++
MAKE_ENV+= AR_${_EMBER_GLYCIN_CC_KEY}=${TOOLDIR}/bin/${_EMBER_GLYCIN_TRIPLET:Uunsupported}-ar
MAKE_ENV+= PKG_CONFIG_ALLOW_CROSS=1
RUSTFLAGS+= -C link-arg=-Wl,-rpath,${PREFIX}/lib
# Panic locations must not retain private source/vendor paths.
RUSTFLAGS+= --remap-path-prefix=${WRKDIR}=.

pre-configure: emberbsd-glycin-rust
.PHONY: emberbsd-glycin-rust
emberbsd-glycin-rust:
	${RUN}${TOOLBASE}/bin/rustc --version | ${GREP} '^rustc 1\.99\.1 '
	${RUN}${TEST} -n "$$(${FIND} ${TOOLBASE}/lib/rustlib/${_EMBER_GLYCIN_RUST_TARGET:Uunsupported}/lib -name 'libstd-*.rlib' -print)"
