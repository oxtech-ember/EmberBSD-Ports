# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); audited Fortran runtime and SDK roles.
.if defined(EMBERBSD_GCC16_FORTRAN_DEVEL)
DISTNAME=	gcc16-fortran-devel-16.2.0
_GCC16_FORTRAN_ROLE=	devel
COMMENT=	GCC16 Fortran development data for a cross SDK
.else
DISTNAME=	gcc16-fortran-runtime-16.2.0
_GCC16_FORTRAN_ROLE=	runtime
COMMENT=	GCC16 Fortran target libraries without compiler tools
.endif
PKGREVISION=	1
CATEGORIES=	lang
MASTER_SITES=	# none
DISTFILES=	# none
HOMEPAGE=	https://gcc.gnu.org/
LICENSE=	gnu-gpl-v3 AND gnu-lgpl-v2.1 AND modified-bsd
ONLY_FOR_PLATFORM=	NetBSD-11.*-x86_64 NetBSD-11.*-aarch64
USE_LANGUAGES=	# none
NO_CONFIGURE=	yes
NO_BUILD=	yes
# The verifier supplies the complete role inventory. Expanding a development
# .la would add shared DSOs which belong to the separate runtime package.
LIBTOOLIZE_PLIST= no
# A complete compiler owns these files until it adopts this runtime split.
CONFLICTS+=	gcc16-[0-9]* gcc16-libs-[0-9]*
DEPENDS+=	gcc16-runtime-16.2.0nb7:../../lang/gcc16-runtime
.if ${_GCC16_FORTRAN_ROLE} == "devel"
DEPENDS+=	gcc16-fortran-runtime-16.2.0nb1:../../lang/gcc16-fortran-runtime
INFO_FILES=	yes
INFO_DIR=	gcc16/share/info
.endif

GCC16_FORTRAN_PYTHON?=
EMBERBSD_SDK_SOURCE?=
GCC16_FORTRAN_WORK?=
GCC16_FORTRAN_ARCHIVE?=
GCC16_FORTRAN_PKGSRC?=	${PKGSRCDIR}
GCC16_FORTRAN_RUNTIME_FILES?=	${PKGSRCDIR}/lang/gcc16-runtime/files
_GCC16_FORTRAN_FILES=	${PKGSRCDIR}/lang/gcc16-fortran-runtime/files
.include "../../mk/bsd.prefs.mk"
.if ${EMBERBSD_CROSS_COMPILER_FAMILY:U} == "clang"
# The Clang profile compiles Fortran with Flang and links LLVM runtimes.
# It never builds GCC16 packages, so it never asks for GCC16 inputs.
PKG_SKIP_REASON+=	"The Clang profile uses Flang and LLVM runtimes, not GCC16 Fortran"
.else
.for _input in GCC16_FORTRAN_PYTHON EMBERBSD_SDK_SOURCE GCC16_FORTRAN_WORK GCC16_FORTRAN_ARCHIVE
.if empty(${_input}:M/*)
PKG_FAIL_REASON+=	"Set ${_input} to its audited absolute build-host path"
.endif
.endfor
.if !empty(GCC16_FORTRAN_PYTHON) && !empty(EMBERBSD_SDK_SOURCE) && !empty(GCC16_FORTRAN_WORK) && !empty(GCC16_FORTRAN_ARCHIVE)
_GCC16_FORTRAN_CMD=	${GCC16_FORTRAN_PYTHON:Q} -I -S -B ${_GCC16_FORTRAN_FILES:Q}/fortran_package.py ${_GCC16_FORTRAN_ROLE:Q}
_GCC16_FORTRAN_ARGS=	${GCC16_FORTRAN_WORK:Q} ${GCC16_FORTRAN_ARCHIVE:Q} ${GCC16_FORTRAN_PKGSRC:Q} --runtime-files ${GCC16_FORTRAN_RUNTIME_FILES:Q} --sdk-source ${EMBERBSD_SDK_SOURCE:Q}
_GCC16_FORTRAN_INFO!=	${_GCC16_FORTRAN_CMD} fields ${_GCC16_FORTRAN_ARGS}
.if empty(_GCC16_FORTRAN_INFO:MGCC_FORTRAN_STAGE_SHA256=*) || empty(_GCC16_FORTRAN_INFO:MGCC_FORTRAN_MACHINE_ARCH=*) || empty(_GCC16_FORTRAN_INFO:MGCC_FORTRAN_ROLE=*)
PKG_FAIL_REASON+=	"Cannot obtain verified Fortran stage fields"
.endif
.for _field in ${_GCC16_FORTRAN_INFO}
${_field:C/=.*//}:= ${_field:C/^[^=]*=//}
BUILD_DEFS+=	${_field:C/=.*//}
.endfor
.if "${GCC_FORTRAN_MACHINE_ARCH:U}" != "${MACHINE_ARCH}" || "${GCC_FORTRAN_ROLE:U}" != "${_GCC16_FORTRAN_ROLE}"
PKG_FAIL_REASON+=	"Fortran stage architecture or role differs from the package"
.endif
GENERATE_PLIST+=	${_GCC16_FORTRAN_CMD} plist ${_GCC16_FORTRAN_ARGS};
.endif
.endif

do-install:
	${RUN} ${_GCC16_FORTRAN_CMD} install ${_GCC16_FORTRAN_ARGS} ${DESTDIR:Q}

.include "../../mk/bsd.pkg.mk"
