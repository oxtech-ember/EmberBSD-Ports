# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Include instead of cargo.mk when the package needs explicit host/target tools.
.if !defined(EMBERBSD_CARGO_MK)
EMBERBSD_CARGO_MK:=

.include "../../mk/bsd.prefs.mk"

# The Rust compiler executes on the host, including for cross packages.
# pkgsrc's native mode avoids adding a target rust-bin through buildlink.
RUST_TYPE=	native
TOOL_DEPENDS+=	rust-bin>=${RUST_REQ:U1.99.1}:../../lang/rust-bin
PYTHON_VERSIONS_ACCEPTED=	315
PYTHON_FOR_BUILD_ONLY=	tool
.include "../../lang/python/tool.mk"
.include "../../lang/rust/cargo.mk"

_EMBER_CARGO_HELPER:=	${.PARSEDIR}/emberbsd-cargo-config.py
EMBER_CARGO_CONFIG?=	${WRKDIR}/.cargo/ember-config.toml
EMBER_CARGO_OUTPUT?=	${WRKDIR}/cargo-target
EMBER_CARGO_TARGET?=
EMBER_CARGO_CONFIGURE_ARGS?=

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
EMBER_CARGO_MODE=	cross
EMBER_CARGO_PREFIX?=	${EMBERBSD_CROSS_HOST_PREFIX:U}
EMBER_CARGO_HOST_CC?=	${NATIVE_CC:U}
EMBER_CARGO_HOST_CXX?=	${NATIVE_CXX:U}
EMBER_CARGO_HOST_AR?=	${NATIVE_AR:U}
EMBER_CARGO_HOST_CPPFLAGS?=	${NATIVE_CPPFLAGS:U}
EMBER_CARGO_HOST_CFLAGS?=	${NATIVE_CFLAGS:U}
EMBER_CARGO_HOST_CXXFLAGS?=	${NATIVE_CXXFLAGS:U}
EMBER_CARGO_HOST_LDFLAGS?=	${NATIVE_LDFLAGS:U}
_EMBER_CARGO_TARGET_ARGS=	--target-cc ${CC:Q} --target-cxx ${CXX:Q} --target-ar ${AR:Q}
_EMBER_CARGO_TARGET_ARGS+= --target-cppflags=${CPPFLAGS:Q} --target-cflags=${CFLAGS:Q}
_EMBER_CARGO_TARGET_ARGS+= --target-cxxflags=${CXXFLAGS:Q} --target-ldflags=${LDFLAGS:Q}
.else
EMBER_CARGO_MODE=	native
EMBER_CARGO_PREFIX?=	${TOOLBASE}
EMBER_CARGO_HOST_CC?=	${CC}
EMBER_CARGO_HOST_CXX?=	${CXX}
EMBER_CARGO_HOST_AR?=	${AR}
EMBER_CARGO_HOST_CPPFLAGS?=	${CPPFLAGS}
EMBER_CARGO_HOST_CFLAGS?=	${CFLAGS}
EMBER_CARGO_HOST_CXXFLAGS?=	${CXXFLAGS}
EMBER_CARGO_HOST_LDFLAGS?=	${LDFLAGS}
.endif

# cargo.mk owns crate fetching, checksums and vendor preparation. This adapter
# only selects tools at configure time, after normal dependency installation.
pre-configure: ember-cargo-configure
.PHONY: ember-cargo-configure
ember-cargo-configure:
	${RUN} ${TEST} ${RUST_TYPE:Q} = native || ${FAIL_MSG} "emberbsd-cargo.mk requires its declared native Rust tool provider"
	${RUN} ${SETENV} ${CONFIGURE_ENV} ${TOOL_PYTHONBIN} -B -I -S ${_EMBER_CARGO_HELPER:Q} configure \
	    --config ${EMBER_CARGO_CONFIG:Q} --vendor ${CARGO_VENDOR_DIR:Q} --output ${EMBER_CARGO_OUTPUT:Q} \
	    --rustc ${EMBER_CARGO_PREFIX:Q}/bin/rustc --shell ${SH:Q} --tool-path ${PATH:Q} \
	    --mode ${EMBER_CARGO_MODE:Q} --target=${EMBER_CARGO_TARGET:Q} \
	    --host-cc ${EMBER_CARGO_HOST_CC:Q} --host-cxx ${EMBER_CARGO_HOST_CXX:Q} --host-ar ${EMBER_CARGO_HOST_AR:Q} \
	    --host-cppflags=${EMBER_CARGO_HOST_CPPFLAGS:Q} --host-cflags=${EMBER_CARGO_HOST_CFLAGS:Q} \
	    --host-cxxflags=${EMBER_CARGO_HOST_CXXFLAGS:Q} --host-ldflags=${EMBER_CARGO_HOST_LDFLAGS:Q} \
	    --rustflags=${RUSTFLAGS:Q} ${_EMBER_CARGO_TARGET_ARGS} ${EMBER_CARGO_CONFIGURE_ARGS}

# Keep pkgsrc's normal Cargo targets, job count, environment and exit status.
CARGO=	${TOOL_PYTHONBIN} -B -I -S ${_EMBER_CARGO_HELPER:Q} run \
	--cargo ${EMBER_CARGO_PREFIX:Q}/bin/cargo --config ${EMBER_CARGO_CONFIG:Q} \
	--source ${CARGO_WRKSRC:Q} --

.endif
