# SPDX-License-Identifier: BSD-2-Clause
# Compose packages from the common compiler-rt full-stage producer.
.include "../../lang/llvm/version.mk"
PKGNAME= ${EMBER_LLVM_CXX_COMPONENT}${EMBER_LLVM_CXX_DEVEL:D-devel}-${LLVM_VERSION}
LLVM_CXX_RUNTIME_REVISION= 1
PKGREVISION= ${LLVM_CXX_RUNTIME_REVISION}
CATEGORIES= lang devel
COMMENT= LLVM ${EMBER_LLVM_CXX_COMPONENT} target runtime
LICENSE= apache-2.0
NO_CONFIGURE= yes
NO_BUILD= yes
NO_CHECKSUM= yes
DISTFILES= # the selected stage is the input
USE_LANGUAGES= # none; the stage producer already selected the compiler
WRKSRC= ${WRKDIR}
PLIST_SRC= ${.CURDIR}/PLIST
EMBER_LLVM_CXX_STAGE?=
EMBER_LLVM_CXX_BASE?=
EMBERBSD_SDK_SOURCE?=
EMBER_LLVM_CXX_PYTHON?=
.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD" || \
    (${MACHINE_ARCH} != "x86_64" && ${MACHINE_ARCH} != "aarch64")
PKG_FAIL_REASON+= "LLVM C++ stage packages require NetBSD amd64 or aarch64 cross build"
.endif
.for _input in EMBER_LLVM_CXX_STAGE EMBER_LLVM_CXX_BASE EMBERBSD_SDK_SOURCE EMBER_LLVM_CXX_PYTHON
.if empty(${_input}:M/*)
PKG_FAIL_REASON+= "Set ${_input} to an absolute selected input"
.endif
.endfor
_LLVM_CXX_TARGET= ${MACHINE_ARCH:S/x86_64/amd64/}
_LLVM_CXX_ROLE= ${EMBER_LLVM_CXX_DEVEL:Ddevel:Uruntime}
_LLVM_CXX_CMD= ${SETENV} EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q} ${EMBER_LLVM_CXX_PYTHON:Q} -B ${PKGSRCDIR}/lang/compiler-rt/files/stage-package.py
_LLVM_CXX_ARGS= --stage ${EMBER_LLVM_CXX_STAGE:Q} --base ${EMBER_LLVM_CXX_BASE:Q} --pkgsrc-root ${PKGSRCDIR:Q} --target ${_LLVM_CXX_TARGET:Q} --component ${EMBER_LLVM_CXX_COMPONENT:Q} --role ${_LLVM_CXX_ROLE:Q}
.if ${EMBER_LLVM_CXX_COMPONENT} == "libcxxabi"
DEPENDS+= libunwind>=${LLVM_VERSION}nb${LLVM_CXX_RUNTIME_REVISION}:../../lang/libunwind
.elif ${EMBER_LLVM_CXX_COMPONENT} == "libcxx"
DEPENDS+= libcxxabi>=${LLVM_VERSION}nb${LLVM_CXX_RUNTIME_REVISION}:../../lang/libcxxabi
DEPENDS+= libunwind>=${LLVM_VERSION}nb${LLVM_CXX_RUNTIME_REVISION}:../../lang/libunwind
.endif
.if defined(EMBER_LLVM_CXX_DEVEL)
DEPENDS+= ${EMBER_LLVM_CXX_COMPONENT}>=${LLVM_VERSION}nb${LLVM_CXX_RUNTIME_REVISION}:../../lang/${EMBER_LLVM_CXX_COMPONENT}
.if ${EMBER_LLVM_CXX_COMPONENT} == "libcxx"
DEPENDS+= libcxxabi-devel>=${LLVM_VERSION}nb${LLVM_CXX_RUNTIME_REVISION}:../../lang/libcxxabi-devel
DEPENDS+= libunwind-devel>=${LLVM_VERSION}nb${LLVM_CXX_RUNTIME_REVISION}:../../lang/libunwind-devel
.elif ${EMBER_LLVM_CXX_COMPONENT} == "libcxxabi"
DEPENDS+= libunwind-devel>=${LLVM_VERSION}nb${LLVM_CXX_RUNTIME_REVISION}:../../lang/libunwind-devel
.endif
.endif
GENERATE_PLIST+= ${_LLVM_CXX_CMD} plist ${_LLVM_CXX_ARGS};
do-install:
	${RUN} test ${PREFIX:Q} = /usr/pkg || { echo "LLVM runtime stage requires PREFIX=/usr/pkg" >&2; exit 1; }
	${RUN} ${_LLVM_CXX_CMD} install ${_LLVM_CXX_ARGS} --destdir ${DESTDIR:Q}
.include "../../mk/bsd.pkg.mk"
