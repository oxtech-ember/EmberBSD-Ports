# $NetBSD: opensbi.mk,v 1.2 2024/06/17 21:53:57 gutteridge Exp $

.include "../../sysutils/opensbi/opensbi-version.mk"
.include "../../sysutils/dtc/Makefile.common"

PKGNAME?=		opensbi-${OPENSBI_BOARD}-${OPENSBI_VERSION:S/-/./}
DISTNAME?=		opensbi-${OPENSBI_VERSION}
DISTINFO_FILE?=		${.CURDIR}/../../sysutils/opensbi/distinfo
CATEGORIES=		sysutils
EXTRACT_SUFX=		.tar.gz

GITHUB_PROJECT?=	opensbi
GITHUB_TAG?=		v${OPENSBI_VERSION}
MASTER_SITES?=		${MASTER_SITE_GITHUB:=riscv-software-src/}
DIST_SUBDIR?=		${GITHUB_PROJECT}

COMMENT=		RISC-V Open Source Supervisor Binary Interface (OpenSBI)
LICENSE=		2-clause-bsd

USE_TOOLS+=		gmake bash
TOOL_DEPENDS+=		dtc>=${DTC_VERSION}:../../sysutils/dtc
TOOL_DEPENDS+=		dtc-libfdt-source-${DTC_VERSION}:../../sysutils/dtc-libfdt-source

OPENSBI_LLVM_PREFIX?=	${EMBERBSD_HOST_PREFIX:U${TOOLBASE}}/bin/
OPENSBI_ENV+=		LLVM=${OPENSBI_LLVM_PREFIX}
OPENSBI_ENV+=		PLATFORM_RISCV_XLEN=${OPENSBI_XLEN:U64}
# LLVM uses CROSS_COMPILE only to select the explicit target triple.
OPENSBI_ENV+=		CROSS_COMPILE=riscv${OPENSBI_XLEN:U64}-unknown-elf-
.if defined(OPENSBI_ISA)
OPENSBI_ENV+=		PLATFORM_RISCV_ISA=${OPENSBI_ISA}
.endif
.if defined(OPENSBI_ABI)
OPENSBI_ENV+=		PLATFORM_RISCV_ABI=${OPENSBI_ABI}
.endif
PATCH_STRIP=		-p1
OPENSBI_ENV+=		PLATFORM=${OPENSBI_PLATFORM}

PYTHON_VERSIONS_INCOMPATIBLE=	27
PYTHON_FOR_BUILD_ONLY=		yes
.include "../../lang/python/tool.mk"

MAKE_ENV+=		${OPENSBI_ENV}

# Compile the common libfdt source with OpenSBI's freestanding environment.
# The package's host libfdt_env.h is intentionally not a target input.
LIBFDT_SOURCE_DIR?=	${EMBERBSD_HOST_PREFIX:U${TOOLBASE}}/share/dtc/libfdt
LIBFDT_SOURCE_FILES=	fdt.c fdt.h fdt_addresses.c fdt_check.c \
			fdt_empty_tree.c fdt_overlay.c fdt_ro.c fdt_rw.c \
			fdt_strerror.c fdt_sw.c fdt_wip.c libfdt.h libfdt_internal.h

post-patch:
.for file in ${LIBFDT_SOURCE_FILES}
	${CP} ${LIBFDT_SOURCE_DIR}/${file} ${WRKSRC}/lib/utils/libfdt/${file}
.endfor

INSTALLATION_DIRS+=	share/opensbi/${OPENSBI_BOARD}

do-install:
.for bin in ${OPENSBI_BIN}
	${INSTALL_DATA} ${WRKSRC}/build/platform/${OPENSBI_PLATFORM}/firmware/${bin} \
	    ${DESTDIR}${PREFIX}/share/opensbi/${OPENSBI_BOARD}
.endfor
