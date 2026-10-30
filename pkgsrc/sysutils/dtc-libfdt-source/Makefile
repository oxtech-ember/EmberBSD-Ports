# libfdt source for freestanding consumers from the shared dtc recipe.
.include "../../sysutils/dtc/Makefile.common"

DISTNAME=		dtc-${DTC_VERSION}
PKGNAME=		dtc-libfdt-source-${DTC_VERSION}
CATEGORIES=		sysutils devel
MASTER_SITES=		https://www.kernel.org/pub/software/utils/dtc/
EXTRACT_SUFX=		.tar.xz
DISTINFO_FILE=		${.CURDIR}/../../sysutils/dtc/distinfo
PATCHDIR=		${.CURDIR}/../../sysutils/dtc/patches

MAINTAINER=		pkgsrc-users@NetBSD.org
HOMEPAGE=		https://www.devicetree.org/
COMMENT=		Common patched libfdt source for freestanding consumers
LICENSE=		2-clause-bsd

USE_LANGUAGES=		# none
NO_CONFIGURE=		yes
NO_BUILD=		yes

INSTALLATION_DIRS+=	share/dtc/libfdt

LIBFDT_SOURCE_FILES=	Makefile.libfdt TODO fdt.c fdt.h fdt_addresses.c \
			fdt_check.c fdt_empty_tree.c fdt_overlay.c fdt_ro.c \
			fdt_rw.c fdt_strerror.c fdt_sw.c fdt_wip.c libfdt.h \
			libfdt_env.h libfdt_internal.h meson.build sbom.cdx.json \
			version.lds

do-install:
.for file in ${LIBFDT_SOURCE_FILES}
	${INSTALL_DATA} ${WRKSRC}/libfdt/${file} ${DESTDIR}${PREFIX}/share/dtc/libfdt/${file}
.endfor
	${INSTALL_DATA} ${WRKSRC}/BSD-2-Clause ${WRKSRC}/GPL ${DESTDIR}${PREFIX}/share/dtc/libfdt

.include "../../mk/bsd.pkg.mk"
