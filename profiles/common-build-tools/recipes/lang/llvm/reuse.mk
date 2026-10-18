# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Explicit reuse of accepted cross LLVM objects.
.if defined(EMBERBSD_LLVM_REUSE_RECEIPT) && ${EMBERBSD_LLVM_REUSE_QUERY:Uno} != "yes"
.if !defined(EMBERBSD_LLVM_DEVEL) || ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD"
PKG_FAIL_REASON+= "LLVM object reuse requires the separate NetBSD cross SDK"
.endif
.for _llvm_input in EMBERBSD_LLVM_REUSE_INPUTS EMBERBSD_LLVM_REUSE_RECEIPT EMBERBSD_LLVM_REUSE_PYTHON
.if empty(${_llvm_input}:M/*) || !exists(${${_llvm_input}})
PKG_FAIL_REASON+= "${_llvm_input} must name an existing absolute file"
.endif
.endfor
.if empty(EMBERBSD_SDK_SOURCE:M/*) || !exists(${EMBERBSD_SDK_SOURCE}/src/emberbsd_sdk/__init__.py)
PKG_FAIL_REASON+= "EMBERBSD_SDK_SOURCE must name the SDK API source"
.endif
.if empty(EMBERBSD_LLVM_REUSE_SHA256)
PKG_FAIL_REASON+= "LLVM object reuse requires the accepted receipt SHA256"
.endif
_EMBERBSD_LLVM_REUSE= yes
NO_BUILD= yes
NO_CONFIGURE= yes
WRKSRC= ${WRKDIR}/llvm-reuse

# Keep private pkgsrc state separate from the accepted source and objects.
do-extract: llvm-verify-reuse
	${MKDIR} ${WRKSRC:Q}
do-patch: llvm-verify-reuse
do-install: llvm-reuse-inputs
	${MKDIR} ${DESTDIR:Q}
	${EMBERBSD_LLVM_REUSE_PYTHON:Q} -B ${FILESDIR:Q}/reuse-package-stage.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} install \
	    ${WRKDIR:Q}/.llvm-reuse-inputs.json ${EMBERBSD_LLVM_REUSE_RECEIPT:Q} \
	    ${EMBERBSD_LLVM_REUSE_SHA256:Q} ${DESTDIR:Q}
.endif

.PHONY: llvm-reuse-inputs llvm-verify-reuse
# This target also prepares the current runtime context before record.
llvm-reuse-inputs:
	${EMBERBSD_LLVM_REUSE_PYTHON:Q} -B ${FILESDIR:Q}/prepare-reuse-inputs.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} \
	    ${EMBERBSD_LLVM_REUSE_INPUTS:Q} ${WRKDIR:Q}/.llvm-reuse-inputs.json ${MAKE:Q} ${.CURDIR:Q} ${EMBERBSD_LLVM_REUSE_RECEIPT:U-:Q}
llvm-verify-reuse: llvm-reuse-inputs
	${EMBERBSD_LLVM_REUSE_PYTHON:Q} -B ${FILESDIR:Q}/reuse-package-stage.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} verify \
	    ${WRKDIR:Q}/.llvm-reuse-inputs.json ${EMBERBSD_LLVM_REUSE_RECEIPT:Q} ${EMBERBSD_LLVM_REUSE_SHA256:Q}
