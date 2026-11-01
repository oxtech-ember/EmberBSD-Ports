# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build-host llvm-config for the target LLVM.
# Cross clang, lld, MLIR and graphics consumers query target LLVM with a host
# executable. It is compiled from the installed target llvm-devel tables and
# the selected native LLVM package; neither LLVM CMake build tree is required.
_EMBERBSD_CROSS_LLVM_STATE=	${WRKOBJDIR:U${PKGSRCDIR}}/.emberbsd-cross/${MACHINE_GNU_PLATFORM}
EMBERBSD_CROSS_LLVM_VERSION?=	${LLVM_VERSION:U23.1.4}
EMBERBSD_CROSS_LLVM_CONFIG_WORK?=	${_EMBERBSD_CROSS_LLVM_STATE}/llvm-config-${EMBERBSD_CROSS_LLVM_VERSION}
EMBERBSD_CROSS_LLVM_CONFIG?=	${EMBERBSD_CROSS_LLVM_CONFIG_WORK}/helper/bin/llvm-config
LLVM_CONFIG_PATH=	${EMBERBSD_CROSS_LLVM_CONFIG}

pre-configure: emberbsd-cross-llvm-config
.PHONY: emberbsd-cross-llvm-config
emberbsd-cross-llvm-config:
	${RUN} ${SETENV} EMBERBSD_HOST_PREFIX=${EMBERBSD_HOST_PREFIX:Q} \
	    EMBERBSD_NATIVE_LD=${NATIVE_LD:Q} NATIVE_CXX=${NATIVE_CXX:Q} \
	    NATIVE_CXXFLAGS=${NATIVE_CXXFLAGS:Q} NATIVE_LDFLAGS=${NATIVE_LDFLAGS:Q} \
	    ${EMBERBSD_CROSS_BUILD_PYTHON:Q} -B ${PKGSRCDIR:Q}/lang/llvm/files/cross-llvm-config.py \
	    ${EMBERBSD_CROSS_LLVM_CONFIG:Q} ${EMBERBSD_CROSS_LLVM_CONFIG_WORK:Q} \
	    ${PKGSRCDIR:Q} ${CROSS_DESTDIR:Q}
