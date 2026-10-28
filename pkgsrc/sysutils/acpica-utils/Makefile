# $NetBSD: Makefile,v 1.17 2023/10/02 11:19:26 rhialto Exp $
#

DISTNAME=	acpica-unix-20260930
PKGNAME=	${DISTNAME:S/-unix-/-utils-/}
CATEGORIES=	sysutils devel
MASTER_SITES=	https://github.com/open-acpica/acpica/releases/download/${PKGVERSION_NOREV}/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.acpica.org/
COMMENT=	Intel ACPI CA Unix utilities
LICENSE=	(modified-bsd OR gnu-gpl-v2) AND cddl-1.0

TESTS_DISTNAME=	${DISTNAME:S/acpica-unix-/acpitests-unix-/}
DISTFILES=	${DEFAULT_DISTFILES}
DISTFILES+=	${TESTS_DISTNAME}${EXTRACT_SUFX}

USE_TOOLS+=	bison flex gm4 gmake bash:test

.include "../../mk/bsd.prefs.mk"
.include "../../mk/compiler.mk"

.if !empty(PKGSRC_COMPILER:Mclang)
MAKE_FLAGS+=	ACPICA_CLANG=yes
.endif

# The upstream makefile probes uname on the build machine. Select the
# platform of the package instead, including in cross builds.
.if ${OPSYS} == "NetBSD"
MAKE_FLAGS+=	ACPI_HOST=_NetBSD
.elif ${OPSYS} == "Darwin"
MAKE_FLAGS+=	ACPI_HOST=_APPLE
.elif ${OPSYS} == "FreeBSD"
MAKE_FLAGS+=	ACPI_HOST=_FreeBSD
.elif ${OPSYS} == "DragonFly"
MAKE_FLAGS+=	ACPI_HOST=_DragonFly
.endif

# Mach-O chained fixups cannot encode pointers at packed byte offsets.
# ACPICA supports natural alignment for its internal pointer-bearing tables.
.if ${OPSYS} == "Darwin"
CFLAGS+=	-DACPI_PACKED_POINTERS_NOT_SUPPORTED
.endif

# These scripts are test inputs and never enter the target package.
REPLACE_INTERPRETER+=	ember-aslts-bash
REPLACE.ember-aslts-bash.old=	.*sh
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
REPLACE.ember-aslts-bash.new=	${EMBERBSD_CROSS_HOST_PREFIX}/bin/bash
.else
REPLACE.ember-aslts-bash.new=	${TOOLS_PATH.bash}
.endif
REPLACE_FILES.ember-aslts-bash+=	tests/aslts.sh
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/Do
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/asltsdiffres
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/asltsrun
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/bugstate/bdemosconc
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/bugstate/bdemossum
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/bugstate/bdemostabs
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/bugstate/parsebuglist
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/common
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/diffproc
REPLACE_FILES.ember-aslts-bash+=	tests/aslts/bin/settings
REPLACE_FILES.ember-aslts-bash+=	tests/templates/templates.sh

post-extract:
	${RUN}${CP} -R ${WRKDIR}/${TESTS_DISTNAME}/tests/. ${WRKSRC}/tests/

do-test:
# ACPICA Tests rely on non-zero exit
## ASL tests
	cd ${WRKSRC}/tests && ./aslts.sh -u
# The 20260930 test archive no longer includes aapits.

.include "../../mk/bsd.pkg.mk"
