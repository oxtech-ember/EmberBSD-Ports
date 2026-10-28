# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build-host llvm-config for the target LLVM.
# Cross clang and lld query the target LLVM with an llvm-config that runs on
# the build host. Before configure, files/cross-llvm-config.py makes it from
# the lang/llvm build tree, which the dependency order builds first. It uses
# the sealed metadata producer. An existing EMBERBSD_CROSS_LLVM_CONFIG is used
# as it is.
_EMBERBSD_CROSS_LLVM_STATE=	${WRKOBJDIR:U${PKGSRCDIR}}/.emberbsd-cross/${MACHINE_GNU_PLATFORM}
EMBERBSD_CROSS_LLVM_CONFIG_WORK?=	${_EMBERBSD_CROSS_LLVM_STATE}/llvm-config-${LLVM_VERSION}
EMBERBSD_CROSS_LLVM_CONFIG?=	${EMBERBSD_CROSS_LLVM_CONFIG_WORK}/sealed/bin/llvm-config
EMBERBSD_CROSS_LLVM_NATIVE_WORK?=	${_EMBERBSD_CROSS_LLVM_STATE}/llvm-native-${LLVM_VERSION}
LLVM_CONFIG_PATH=	${EMBERBSD_CROSS_LLVM_CONFIG}

pre-configure: emberbsd-cross-llvm-config
.PHONY: emberbsd-cross-llvm-config
emberbsd-cross-llvm-config:
	${RUN} ${SETENV} EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q} \
	    EMBERBSD_HOST_PREFIX=${EMBERBSD_HOST_PREFIX:Q} \
	    ${EMBERBSD_CROSS_BUILD_PYTHON:Q} -B ${PKGSRCDIR:Q}/lang/llvm/files/cross-llvm-config.py \
	    ${EMBERBSD_CROSS_LLVM_CONFIG:Q} ${EMBERBSD_CROSS_LLVM_CONFIG_WORK:Q} \
	    ${EMBERBSD_CROSS_LLVM_NATIVE_WORK:Q} ${PKGSRCDIR:Q} ${CROSS_DESTDIR:Q} \
	    ${DISTDIR:Q}/${DISTNAME:Q}${EXTRACT_SUFX:Q} ${MAKE:Q}
