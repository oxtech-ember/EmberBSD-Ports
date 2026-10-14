# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Included only for cross builds, after
# the librsvg cross recipe in profiles/common-graphics.
RUST_TYPE= native
TOOL_DEPENDS+= rust-bin-1.99.0{,nb[0-9]*}:../../lang/rust-bin
TOOL_DEPENDS+= rust-std-aarch64-netbsd-1.99.0{,nb[0-9]*}:../../lang/rust-std-aarch64-netbsd

MESON_ARGS+= -Dtriplet=aarch64-unknown-netbsd
# Meson must compile its rust sanity check for the target triple.
MESON_CROSS_VARS+= rust_target
MESON_CROSS.rust_target= 'aarch64-unknown-netbsd'
# Declare rustc as the cross rust compiler so sanity checks use the target.
MESON_BINARIES+= rustc
MESON_BINARY.rustc= ${TOOLBASE}/bin/rustc

# The installed-library step inspects target ELF, not Mach-O.
MESON_BINARIES+= nm strip
MESON_BINARY.nm= ${TOOLDIR}/bin/aarch64--netbsd-nm
MESON_BINARY.strip= ${TOOLDIR}/bin/aarch64--netbsd-strip

# pkgsrc's native Rust mode avoids selecting a target compiler package.
TOOLS_CREATE+= cargo rustc
.for _rust_tool in cargo rustc
TOOLS_PATH.${_rust_tool}= ${TOOLBASE}/bin/${_rust_tool}
.endfor
MAKE_ENV+= RUSTC=${TOOLBASE}/bin/rustc
MAKE_ENV+= CARGO_NET_OFFLINE=true CARGO_BUILD_JOBS=${MAKE_JOBS:U1}
MAKE_ENV+= CARGO_TARGET_AARCH64_UNKNOWN_NETBSD_LINKER=${WRAPPER_BINDIR}/cc
MAKE_ENV+= CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=${EMBERBSD_CROSS_BUILD_CC}
MAKE_ENV+= HOST_CC=${EMBERBSD_CROSS_BUILD_CC} HOST_CXX=${EMBERBSD_CROSS_BUILD_CXX}
MAKE_ENV+= HOST_AR=/usr/bin/ar
MAKE_ENV+= HOST_CFLAGS= HOST_CXXFLAGS=
MAKE_ENV+= CC_aarch64_unknown_netbsd=${WRAPPER_BINDIR}/cc
MAKE_ENV+= CXX_aarch64_unknown_netbsd=${WRAPPER_BINDIR}/c++
MAKE_ENV+= AR_aarch64_unknown_netbsd=${TOOLDIR}/bin/aarch64--netbsd-ar
MAKE_ENV+= PKG_CONFIG_ALLOW_CROSS=1
RUSTFLAGS+= -C link-arg=-Wl,-rpath,${PREFIX}/lib
# Panic locations must not retain private source/vendor paths.
RUSTFLAGS+= --remap-path-prefix=${WRKDIR}=.

pre-configure: emberbsd-glycin-rust
.PHONY: emberbsd-glycin-rust
emberbsd-glycin-rust:
	${RUN}${TOOLBASE}/bin/rustc --version | ${GREP} '^rustc 1\.99\.0 '
	${RUN}${TEST} -n "$$(${FIND} ${TOOLBASE}/lib/rustlib/aarch64-unknown-netbsd/lib -name 'libstd-*.rlib' -print)"
