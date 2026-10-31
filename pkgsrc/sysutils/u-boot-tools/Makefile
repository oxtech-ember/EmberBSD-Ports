# Native U-Boot image tools from the common, patched source package.
.include "../../sysutils/u-boot-source/Makefile.common"

DISTNAME= u-boot-tools-${UBOOT_SOURCE_VERSION}
PKGREVISION= ${UBOOT_SOURCE_REVISION}
CATEGORIES= sysutils
DISTFILES= # none
HOMEPAGE= https://www.denx.de/wiki/U-Boot
COMMENT= U-Boot image creation and inspection tools
LICENSE= gnu-gpl-v2 AND modified-bsd AND 2-clause-bsd AND mit

TOOL_DEPENDS+= u-boot-source-${UBOOT_SOURCE_VERSION}nb${UBOOT_SOURCE_REVISION}:../../sysutils/u-boot-source
USE_TOOLS+= gmake bash bison flex pkg-config
NO_CHECKSUM= yes
WRKSRC= ${WRKDIR}/source
UBOOT_TOOLS_OBJ= ${WRKDIR}/obj

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+= "u-boot-tools is a native tool; cross consumers must use TOOL_DEPENDS"
.endif

INSTALLATION_DIRS= bin share/doc/u-boot-tools

do-extract:
	${MKDIR} ${WRKSRC} ${UBOOT_TOOLS_OBJ}
	${CP} -R ${UBOOT_SOURCE_DIR}/. ${WRKSRC}/

do-configure:
	${GMAKE} -C ${WRKSRC} O=${UBOOT_TOOLS_OBJ} ARCH=sandbox \
	    CC=${CC:Q} HOSTCC=${CC:Q} tools-only_defconfig
	${TOOLBASE}/bin/bash ${WRKSRC}/scripts/config --file ${UBOOT_TOOLS_OBJ}/.config \
	    --disable TOOLS_MKEFICAPSULE

do-build:
	${GMAKE} -j${MAKE_JOBS:U1} -C ${WRKSRC} O=${UBOOT_TOOLS_OBJ} ARCH=sandbox \
	    CC=${CC:Q} HOSTCC=${CC:Q} HOSTCFLAGS=${CFLAGS:Q} \
	    HOSTLDFLAGS=${LDFLAGS:Q} tools-only

do-install:
	${INSTALL_PROGRAM} ${UBOOT_TOOLS_OBJ}/tools/mkimage ${DESTDIR}${PREFIX}/bin
	${INSTALL_PROGRAM} ${UBOOT_TOOLS_OBJ}/tools/dumpimage ${DESTDIR}${PREFIX}/bin
	${INSTALL_DATA} ${WRKSRC}/Licenses/README ${DESTDIR}${PREFIX}/share/doc/u-boot-tools
	${INSTALL_DATA} ${WRKSRC}/Licenses/gpl-2.0.txt ${DESTDIR}${PREFIX}/share/doc/u-boot-tools
	${INSTALL_DATA} ${WRKSRC}/Licenses/bsd-2-clause.txt ${DESTDIR}${PREFIX}/share/doc/u-boot-tools
	${INSTALL_DATA} ${WRKSRC}/Licenses/bsd-3-clause.txt ${DESTDIR}${PREFIX}/share/doc/u-boot-tools
	${INSTALL_DATA} ${WRKSRC}/Licenses/mit.txt ${DESTDIR}${PREFIX}/share/doc/u-boot-tools

.include "../../sysutils/dtc/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
