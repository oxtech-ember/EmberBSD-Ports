# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native Rust tools and real target GType queries.
# Included only for cross builds. Rust's target ABI name remains unchanged.
RUST_TYPE= native
TOOL_DEPENDS+= rust-bin-1.99.1{,nb[0-9]*}:../../lang/rust-bin
BUILD_DEPENDS+= glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection

EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
.if ${_EMBER_GI_TARGET:U} == "aarch64"
_EMBER_RSVG_RUST_TARGET= aarch64-unknown-netbsd
_EMBER_RSVG_STD_PACKAGE= rust-std-aarch64-netbsd
.elif ${_EMBER_GI_TARGET:U} == "amd64"
_EMBER_RSVG_RUST_TARGET= x86_64-unknown-netbsd
_EMBER_RSVG_STD_PACKAGE= rust-std-x86_64-netbsd
.else
PKG_FAIL_REASON+= "librsvg requires a supported GI cross target"
.endif
RUST_TARGET= ${_EMBER_RSVG_RUST_TARGET:Uunsupported}
.if "${RUST_TARGET}" != "${_EMBER_RSVG_RUST_TARGET:U}"
PKG_FAIL_REASON+= "librsvg Rust target must match the selected GI/GNU target"
.endif
.if defined(_EMBER_RSVG_STD_PACKAGE)
TOOL_DEPENDS+= ${_EMBER_RSVG_STD_PACKAGE}-1.99.1{,nb[0-9]*}:../../lang/${_EMBER_RSVG_STD_PACKAGE}
.endif
_EMBER_RSVG_RUST_KEY= ${RUST_TARGET:tu:S/-/_/g}
_EMBER_RSVG_CC_KEY= ${RUST_TARGET:S/-/_/g}
BUILDLINK_API_DEPENDS.gobject-introspection+= gobject-introspection>=1.86.0nb5
MESON_ARGS+= -Dtriplet=${RUST_TARGET} -Dintrospection=enabled
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
# pkg-config rebases lookup paths, but installation needs the target prefix.
MESON_CROSS_VARS+= emberbsd_pixbuf_module_dir
MESON_CROSS.emberbsd_pixbuf_module_dir= '${PREFIX}/lib/gdk-pixbuf-2.0/2.10.0/loaders'
# The symbol exporter and install step inspect target ELF, not Mach-O.
MESON_BINARIES+= nm strip
MESON_BINARY.nm= ${TOOLDIR}/bin/${_EMBER_GI_TRIPLET}-nm
MESON_BINARY.strip= ${TOOLDIR}/bin/${_EMBER_GI_TRIPLET}-strip
# The native scanner canonicalizes include paths. Map that sysroot spelling
# back into the declared buildlink tree instead of admitting host directories.
EMBERBSD_RSVG_REAL_SYSROOT!= cd ${CROSS_DESTDIR:Q} && pwd -P
BUILDLINK_TRANSFORM+= I:${EMBERBSD_RSVG_REAL_SYSROOT}${PREFIX}:${BUILDLINK_DIR}

# pkgsrc's native Rust mode avoids selecting a target compiler package.
# The declared host packages still own and validate these tools and target std.
TOOLS_CREATE+= cargo rustc cargo-cbuild
.for _rust_tool in cargo rustc cargo-cbuild
TOOLS_PATH.${_rust_tool}= ${TOOLBASE}/bin/${_rust_tool}
.endfor
MAKE_ENV+= RUSTC=${TOOLBASE}/bin/rustc
MAKE_ENV+= CARGO_NET_OFFLINE=true CARGO_BUILD_JOBS=${MAKE_JOBS:U1}
MAKE_ENV+= CARGO_TARGET_${_EMBER_RSVG_RUST_KEY}_LINKER=${WRAPPER_BINDIR}/cc
# Dependencies may not be installed during the first make parse. Once present,
# derive the host key only from the matching native compiler's actual identity.
.if exists(${TOOLBASE}/bin/rustc)
_EMBER_RSVG_RUST_HOST!= ${TOOLBASE:Q}/bin/rustc -vV | ${EMBERBSD_NATIVE_AWK:Q} \
    '/^release: / {release=$$2} /^commit-hash: / {commit=$$2} /^host: / {host=$$2} \
    END {if (release == "1.99.1" && commit == "58cf8f9c35b355199727627d07ae34a4e2846d67") print host; else exit 1}'
.if empty(_EMBER_RSVG_RUST_HOST) || !empty(_EMBER_RSVG_RUST_HOST:C/[A-Za-z0-9_-]//g)
PKG_FAIL_REASON+= "librsvg requires the shared official native Rust 1.99.1 provider"
.else
_EMBER_RSVG_HOST_KEY= ${_EMBER_RSVG_RUST_HOST:tu:S/-/_/g}
MAKE_ENV+= CARGO_TARGET_${_EMBER_RSVG_HOST_KEY}_LINKER=${EMBERBSD_CROSS_BUILD_CC}
.endif
.endif
MAKE_ENV+= HOST_CC=${EMBERBSD_CROSS_BUILD_CC} HOST_CXX=${EMBERBSD_CROSS_BUILD_CXX}
MAKE_ENV+= HOST_AR=${EMBERBSD_CROSS_BUILD_AR}
MAKE_ENV+= HOST_CFLAGS= HOST_CXXFLAGS=
MAKE_ENV+= CC_${_EMBER_RSVG_CC_KEY}=${WRAPPER_BINDIR}/cc
MAKE_ENV+= CXX_${_EMBER_RSVG_CC_KEY}=${WRAPPER_BINDIR}/c++
MAKE_ENV+= AR_${_EMBER_RSVG_CC_KEY}=${TOOLDIR}/bin/${_EMBER_GI_TRIPLET}-ar
MAKE_ENV+= PKG_CONFIG_ALLOW_CROSS=1
RUSTFLAGS+= -C link-arg=-Wl,-rpath,${PREFIX}/lib
# Panic locations must not retain private source/vendor paths in the package.
RUSTFLAGS+= --remap-path-prefix=${WRKDIR}=.

pre-configure: emberbsd-librsvg-rust
.PHONY: emberbsd-librsvg-rust
emberbsd-librsvg-rust:
	${RUN}set -eu; \
	rustc=${TOOLBASE:Q}/bin/rustc; cargo=${TOOLBASE:Q}/bin/cargo; \
	"$$rustc" -vV | ${EMBERBSD_NATIVE_AWK:Q} -v expected=${_EMBER_RSVG_RUST_HOST:Q} \
	    '/^release: / {release=$$2} /^commit-hash: / {commit=$$2} /^host: / {host=$$2} \
	     END {if (release != "1.99.1" || commit != "58cf8f9c35b355199727627d07ae34a4e2846d67" || host != expected) exit 1}'; \
	test '${_EMBER_RSVG_RUST_HOST}' != '${RUST_TARGET}'; \
	"$$cargo" -V | ${GREP} -q '^cargo 1[.]99[.]0 '; \
	${SH:Q} ${FILESDIR:Q}/verify-target-drivers.sh ${WRAPPER_BINDIR:Q}/cc ${WRAPPER_BINDIR:Q}/c++ \
	    ${_EMBER_GI_TRIPLET:Q} ${RUST_TARGET:Q}; \
	host=$$(CDPATH= cd ${TOOLBASE:Q} && pwd -P); \
	component=$$("$$rustc" --target '${RUST_TARGET}' --print target-libdir); \
	component=$$(CDPATH= cd "$$component" && pwd -P); \
	test "$$component" = "$$host/lib/rustlib/${RUST_TARGET}/lib"; \
	for library in std core; do \
	    set -- "$$component/lib$$library-"*.rlib; \
	    test "$$#" -eq 1 && test -f "$$1" && test ! -L "$$1" && test -s "$$1" || { \
	        echo "Missing, ambiguous or linked target $$library rlib." >&2; exit 1; }; \
	done; \
	probe=${WRKDIR:Q}/target-std-check.rmeta; test ! -L "$$probe"; \
	if test -e "$$probe"; then test -f "$$probe"; rm "$$probe"; fi; \
	printf 'pub fn target_std_check() -> std::string::String { std::string::String::new() }\n' | \
	    "$$rustc" --crate-type=lib --target '${RUST_TARGET}' --emit=metadata --edition=2024 -o "$$probe" -; \
	test -s "$$probe"
