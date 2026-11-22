# Origin: EmberBSD (AI-assisted). Header-only extraction; ModemManagerQt
# needs only the constant and enum headers, no daemon or GLib library.

DISTNAME=	ModemManager-1.24.2
PKGNAME=	${DISTNAME:S/ModemManager-/modemmanager-headers-/}
CATEGORIES=	devel
MASTER_SITES=	https://gitlab.freedesktop.org/mobile-broadband/ModemManager/-/archive/${PKGVERSION_NOREV}/
EXTRACT_SUFX=	.tar.gz

HOMEPAGE=	https://www.freedesktop.org/wiki/Software/ModemManager/
COMMENT=	ModemManager DBus interface constants (header-only)
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2

NO_BUILD=	yes
USE_LANGUAGES=	# none
USE_TOOLS+=	sed
TOOL_DEPENDS+=	libxslt>=1.1:../../textproc/libxslt

MM_VERSION_PARTS=	${PKGVERSION_NOREV:S/./ /g}

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/include/ModemManager
	${INSTALL_DATA} ${WRKSRC}/include/ModemManager*.h \
		${DESTDIR}${PREFIX}/include/ModemManager/
	${SED} -e 's|@VERSION@|${PKGVERSION_NOREV}|g' \
		-e 's|@MM_MAJOR_VERSION@|${MM_VERSION_PARTS:[1]}|g' \
		-e 's|@MM_MINOR_VERSION@|${MM_VERSION_PARTS:[2]}|g' \
		-e 's|@MM_MICRO_VERSION@|${MM_VERSION_PARTS:[3]}|g' \
		${WRKSRC}/include/ModemManager-version.h.in > \
		${DESTDIR}${PREFIX}/include/ModemManager/ModemManager-version.h
	${TOOLBASE}/bin/xsltproc --xinclude --nonet --output \
		${DESTDIR}${PREFIX}/include/ModemManager/ModemManager-names.h \
		${WRKSRC}/build-aux/header-generator.xsl ${WRKSRC}/introspection/all.xml
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/lib/pkgconfig
	${SED} -e 's|@prefix@|${PREFIX}|g' \
		-e 's|@exec_prefix@|$${prefix}|g' \
		-e 's|@libdir@|$${exec_prefix}/lib|g' \
		-e 's|@includedir@|$${prefix}/include|g' \
		-e 's|@VERSION@|${PKGVERSION_NOREV}|g' \
		-e 's|^Cflags: |Cflags: -I$${includedir} |' \
		${WRKSRC}/data/ModemManager.pc.in > \
		${DESTDIR}${PREFIX}/lib/pkgconfig/ModemManager.pc

.include "../../mk/bsd.pkg.mk"
