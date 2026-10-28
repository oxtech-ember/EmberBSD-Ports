# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Apply the common source patches after pkgsrc has populated CARGO_VENDOR_DIR.
.if !defined(EMBERBSD_CARGO_PATCHES_MK)
EMBERBSD_CARGO_PATCHES_MK:=
EMBER_CARGO_PATCH_SET?= no
EMBER_CARGO_PATCH_TOOL?= ${EMBER_CARGO_PREFIX}/bin/gpatch
_EMBER_CARGO_PATCH_HELPER:= ${.PARSEDIR:tA}/emberbsd-cargo-patches.py
_EMBER_CARGO_PATCH_REGISTRY:= ${.PARSEDIR:tA}/emberbsd-cargo-patches
pre-configure: ember-cargo-patches
.PHONY: ember-cargo-patches
ember-cargo-patches:
.if ${EMBER_CARGO_PATCH_SET:tl} == "yes"
	${RUN} ${TOOL_PYTHONBIN} -B -I -S ${_EMBER_CARGO_PATCH_HELPER:Q} \
	    --vendor ${CARGO_VENDOR_DIR:Q} --registry ${_EMBER_CARGO_PATCH_REGISTRY:Q} \
	    --prefix ${EMBER_CARGO_PREFIX:Q} --patch ${EMBER_CARGO_PATCH_TOOL:Q}
.endif
.endif
