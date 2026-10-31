# Common patched U-Boot source for firmware consumers.
.include "../../sysutils/u-boot-source/Makefile.common"
.include "../../sysutils/dtc/Makefile.common"
.include "../../devel/zlib/Makefile.common"

DISTNAME= u-boot-${UBOOT_SOURCE_VERSION}
PKGNAME= u-boot-source-${UBOOT_SOURCE_VERSION}
PKGREVISION= 6
DIST_SUBDIR= u-boot
CATEGORIES= sysutils
MASTER_SITES= ${MASTER_SITE_GITHUB:=u-boot/}
GITHUB_PROJECT= u-boot
GITHUB_TAG= v${UBOOT_SOURCE_VERSION}
EXTRACT_SUFX= .tar.gz
PATCH_STRIP= -p1
HOMEPAGE= https://www.denx.de/wiki/U-Boot
COMMENT= Common patched U-Boot sources for firmware consumers
LICENSE= gnu-gpl-v2 AND modified-bsd AND 2-clause-bsd AND zlib AND mit AND \
 gnu-lgpl-v2.1 AND isc AND unicode AND cc0-1.0-universal AND cc-by-v4.0 AND \
 cc-by-sa-v4.0 AND uboot-BSD-2-Clause-Patent AND uboot-BSD-3-Clause-Clear AND \
 uboot-LZMA-SDK-9.22 AND uboot-Intel AND uboot-eCos-2.0 AND uboot-bzip2-1.0.6

USE_LANGUAGES= # none
USE_TOOLS+= find
NO_CONFIGURE= yes
NO_BUILD= yes
TOOL_DEPENDS+= dtc-libfdt-source-${DTC_VERSION}:../../sysutils/dtc-libfdt-source
TOOL_DEPENDS+= zlib-source-${ZLIB_VERSION}nb${ZLIB_PATCH_REVISION}:../../devel/zlib-source

UBOOT_HOST_PREFIX?= ${EMBERBSD_HOST_PREFIX:U${TOOLBASE}}
LIBFDT_SOURCE_DIR?= ${UBOOT_HOST_PREFIX}/share/dtc/libfdt
ZLIB_SOURCE_DIR?= ${UBOOT_HOST_PREFIX}/share/zlib-source/core
LIBFDT_SOURCE_FILES= BSD-2-Clause GPL Makefile.libfdt fdt.c fdt.h fdt_addresses.c fdt_check.c fdt_empty_tree.c fdt_overlay.c fdt_ro.c fdt_rw.c fdt_strerror.c fdt_sw.c fdt_wip.c libfdt.h libfdt_internal.h

UBOOT_EXTRA_LICENSES= uboot-BSD-2-Clause-Patent uboot-BSD-3-Clause-Clear \
 uboot-LZMA-SDK-9.22 uboot-Intel uboot-eCos-2.0 uboot-bzip2-1.0.6

post-extract:
	${CP} -R ${FILESDIR}/. ${WRKSRC}/
.for file in ${UBOOT_EXTRA_LICENSES}
	${CP} ${PKGSRCDIR}/licenses/${file} ${WRKSRC}/emberbsd-licenses/${file}
.endfor
post-patch:
.for file in ${LIBFDT_SOURCE_FILES}
	${CP} ${LIBFDT_SOURCE_DIR}/${file} ${WRKSRC}/scripts/dtc/libfdt/${file}
.endfor
	${CP} ${ZLIB_SOURCE_DIR}/*.[ch] ${WRKSRC}/lib/zlib/
	${CP} ${ZLIB_SOURCE_DIR}/LICENSE ${WRKSRC}/lib/zlib/LICENSE.upstream
	${RM} -f ${WRKSRC}/lib/zlib/zlib.c
	${RM} -rf ${WRKSRC}/lib/mbedtls/external/mbedtls
	# The pinned archive has no .orig files; these are patch backup copies.
	${FIND} ${WRKSRC} -type f -name "*.orig" -exec ${RM} -f {} +

INSTALLATION_DIRS+= share/u-boot-source
do-install:
	${CP} -R ${WRKSRC}/. ${DESTDIR}${PREFIX}/share/u-boot-source/

.include "../../mk/bsd.pkg.mk"
