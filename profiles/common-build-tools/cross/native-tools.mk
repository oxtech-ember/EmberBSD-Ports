# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Shared native prefix selection.
# These names hold verifier results and SDK-rendered expectations.
# Command-line make variables take precedence over all ordinary assignments.
.if !empty(.MAKEOVERRIDES:M_EMBER_SDK_*) || !empty(.MAKEOVERRIDES:M_EMBER_NATIVE_*)
.error Do not override reserved SDK native selection variables
.endif
.for _ember_native_input in EMBERBSD_SDK_SOURCE EMBERBSD_HOST_PREFIX \
    EMBERBSD_NATIVE_TOOLSET_MAKECONF
.if !defined(${_ember_native_input}) || empty(${_ember_native_input})
.error Set ${_ember_native_input} for the selected Ports host prefix
.endif
.endfor
EMBERBSD_HOST_PYTHON?=${EMBERBSD_HOST_PREFIX}/bin/python3.15
EMBERBSD_HOST_COMPILER_FAMILY?=clang
EMBERBSD_HOST_FETCH_MODE?=fetch
# Check selected paths before the include can assign native commands.
# The SDK checks the prefix. Ports owns this make-variable mapping.
# A run verifies one selection once: recursive queries inherit the result,
# and scripts/cross-bulk.sh passes it to each of its bmake calls.
_EMBER_NATIVE_CXX_BINDING_ARG=
.if defined(EMBERBSD_NATIVE_CXX_BINDING_RECORD) && !empty(EMBERBSD_NATIVE_CXX_BINDING_RECORD)
_EMBER_NATIVE_CXX_BINDING_ARG= --native-cxx-binding-record ${EMBERBSD_NATIVE_CXX_BINDING_RECORD:Q}
.endif
_EMBER_NATIVE_TOOLSET_KEY:=${EMBERBSD_SDK_SOURCE}|${EMBERBSD_HOST_PREFIX}|${EMBERBSD_HOST_COMPILER_FAMILY}|${EMBERBSD_HOST_FETCH_MODE}|${EMBERBSD_NATIVE_TOOLSET_MAKECONF}|${EMBERBSD_NATIVE_CXX_BINDING_RECORD:U}
.if "${EMBERBSD_NATIVE_TOOLSET_VERIFIED:U}" != "${_EMBER_NATIVE_TOOLSET_KEY}"
_EMBER_NATIVE_TOOLSET_CHECK!= ${EMBERBSD_HOST_PYTHON:Q} -B -E -S \
    ${.PARSEDIR:Q}/prepare-native-tools.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} verify \
    --host-prefix ${EMBERBSD_HOST_PREFIX:Q} \
    --compiler-family ${EMBERBSD_HOST_COMPILER_FAMILY:Q} \
    --fetch-mode ${EMBERBSD_HOST_FETCH_MODE:Q} ${_EMBER_NATIVE_CXX_BINDING_ARG} \
    --makeconf ${EMBERBSD_NATIVE_TOOLSET_MAKECONF:Q}
.if "${_EMBER_NATIVE_TOOLSET_CHECK}" != "VERIFIED"
.error The host prefix or its native include is invalid
.endif
EMBERBSD_NATIVE_TOOLSET_VERIFIED:=${_EMBER_NATIVE_TOOLSET_KEY}
.export EMBERBSD_NATIVE_TOOLSET_VERIFIED
.endif
.include "${EMBERBSD_NATIVE_TOOLSET_MAKECONF}"
