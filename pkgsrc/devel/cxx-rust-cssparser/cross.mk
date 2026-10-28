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
PKG_FAIL_REASON+= "cxx-rust-cssparser requires matching NetBSD 11 Rust and compiler targets"
.endif
TOOL_DEPENDS+= rust-bin-1.99.1{,nb[0-9]*}:../../lang/rust-bin
.if defined(_EMBER_CSS_STD_PACKAGE)
TOOL_DEPENDS+= ${_EMBER_CSS_STD_PACKAGE}-1.99.1{,nb[0-9]*}:../../lang/${_EMBER_CSS_STD_PACKAGE}
.endif
# The cross profile selects the native host compiler independently.
_EMBER_CSS_HOST_CC= ${EMBERBSD_CROSS_BUILD_CC:U}
_EMBER_CSS_HOST_CXX= ${EMBERBSD_CROSS_BUILD_CXX:U}
_EMBER_CSS_HOST_AR= ${EMBERBSD_CROSS_BUILD_AR:U}
.for host_driver in _EMBER_CSS_HOST_CC _EMBER_CSS_HOST_CXX _EMBER_CSS_HOST_AR
.if empty(${host_driver}:M/*) || !exists(${${host_driver}})
PKG_FAIL_REASON+= "cxx-rust-cssparser requires absolute native build compilers"
.endif
.endfor
_EMBER_CSS_CC= ${WRAPPER_BINDIR}/cc
_EMBER_CSS_CXX= ${WRAPPER_BINDIR}/c++
_EMBER_CSS_PREFIX= ${EMBERBSD_CROSS_HOST_PREFIX}

.PHONY: ember-css-check-cross
ember-css-check-cross:
	${RUN} ${SH} ${FILESDIR:Q}/verify-cross-inputs.sh \
	    ${_EMBER_CSS_PREFIX:Q} ${RUST_TARGET:Q} ${_EMBER_CSS_GNU_TRIPLET:Q} \
	    ${_EMBER_CSS_CC:Q} ${_EMBER_CSS_CXX:Q} ${_PKGSRCDIR:Q}/mk/emberbsd-verify-target-drivers.sh \
	    ${SH:Q} ${WRKDIR:Q}/target-std-check.rmeta > ${WRKDIR:Q}/rust-host.txt
.else
_EMBER_CSS_PREFIX= ${TOOLBASE}
_EMBER_CSS_HOST_CC= ${WRAPPER_BINDIR}/cc
_EMBER_CSS_HOST_CXX= ${WRAPPER_BINDIR}/c++
_EMBER_CSS_HOST_AR= ${AR}
_EMBER_CSS_CC= ${WRAPPER_BINDIR}/cc
_EMBER_CSS_CXX= ${WRAPPER_BINDIR}/c++
.PHONY: ember-css-check-cross
ember-css-check-cross:
.endif
