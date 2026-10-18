# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted package of prebuilt, audited target runtime DSOs.
DISTNAME=	gcc16-runtime-16.2.0
PKGREVISION=	1
CATEGORIES=	lang
MASTER_SITES=	# none
DISTFILES=	# none
HOMEPAGE=	https://gcc.gnu.org/
COMMENT=	GCC16 target shared runtime without compiler tools
LICENSE=	gnu-gpl-v3

CONFLICTS+=	gcc16-[0-9]* gcc16-libs-[0-9]*
ONLY_FOR_PLATFORM=	NetBSD-11.*-x86_64 NetBSD-11.*-aarch64
USE_LANGUAGES=	# none
NO_CONFIGURE=	yes
NO_BUILD=	yes

# These are build-host paths. Never install Ruby or build tools on the target.
# The stage and GCC archive remain external. The verifier does not change them.
GCC16_RUNTIME_RUBY?=
GCC16_RUNTIME_WORK?=
GCC16_RUNTIME_ARCHIVE?=
GCC16_RUNTIME_PKGSRC?=	${.CURDIR}/../..

FILESDIR?=	${.CURDIR}/files

.include "../../mk/bsd.prefs.mk"

.for _input in GCC16_RUNTIME_RUBY GCC16_RUNTIME_WORK GCC16_RUNTIME_ARCHIVE
.if empty(${_input})
PKG_FAIL_REASON+=	"Set ${_input} to its audited absolute build-host path."
.endif
.endfor

.if !empty(GCC16_RUNTIME_RUBY) && !empty(GCC16_RUNTIME_WORK) && !empty(GCC16_RUNTIME_ARCHIVE)
_GCC16_RUNTIME_ARGS=	${GCC16_RUNTIME_WORK:Q} ${GCC16_RUNTIME_ARCHIVE:Q} ${GCC16_RUNTIME_PKGSRC:Q}
_GCC16_RUNTIME_INFO!=	${GCC16_RUNTIME_RUBY:Q} ${FILESDIR:Q}/runtime.rb fields ${_GCC16_RUNTIME_ARGS}
.if empty(_GCC16_RUNTIME_INFO:MGCC_SOURCE_SHA256=*) || empty(_GCC16_RUNTIME_INFO:MGCC_RECIPE_SHA256=*) || empty(_GCC16_RUNTIME_INFO:MGCC_RUNTIME_INPUTS_SHA256=*) || empty(_GCC16_RUNTIME_INFO:MGCC_RUNTIME_STAGE_SHA256=*) || empty(_GCC16_RUNTIME_INFO:MGCC_RUNTIME_TARGET=*) || empty(_GCC16_RUNTIME_INFO:MGCC_RUNTIME_TRIPLET=*) || empty(_GCC16_RUNTIME_INFO:MGCC_RUNTIME_MACHINE_ARCH=*)
PKG_FAIL_REASON+= "Cannot obtain audited runtime provenance; stage verification failed."
.endif
.for _definition in ${_GCC16_RUNTIME_INFO}
${_definition:C/=.*//}:=	${_definition:C/^[^=]*=//}
BUILD_DEFS+=	${_definition:C/=.*//}
.endfor
.if "${GCC_RUNTIME_MACHINE_ARCH:U}" != "${MACHINE_ARCH}"
PKG_FAIL_REASON+= "Audited runtime architecture does not match the package target MACHINE_ARCH."
.endif
.endif

GENERATE_PLIST+=	${GCC16_RUNTIME_RUBY:Q} ${FILESDIR:Q}/runtime.rb plist ${_GCC16_RUNTIME_ARGS};

do-install:
	${RUN} ${GCC16_RUNTIME_RUBY:Q} ${FILESDIR:Q}/runtime.rb install ${_GCC16_RUNTIME_ARGS} ${DESTDIR:Q}

.include "../../mk/bsd.pkg.mk"
