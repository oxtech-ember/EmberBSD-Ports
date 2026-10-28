# Origin: EmberBSD (AI-assisted). Header-only extraction; ModemManagerQt
# needs only the constant and enum headers, no daemon or GLib library.

DISTNAME=	ModemManager-1.22.0
PKGNAME=	modemmanager-headers-1.22.0
CATEGORIES=	devel
MASTER_SITES=	https://gitlab.freedesktop.org/mobile-broadband/ModemManager/-/archive/1.22.0/
EXTRACT_SUFX=	.tar.gz

HOMEPAGE=	https://www.freedesktop.org/wiki/Software/ModemManager/
COMMENT=	ModemManager DBus interface constants (header-only)
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2

WRKSRC=		${WRKDIR}/ModemManager-1.22.0
NO_BUILD=	yes
USE_LANGUAGES=	# none
# The upstream names header generator runs on the build host.

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/include/ModemManager
	${INSTALL_DATA} ${WRKSRC}/include/ModemManager*.h \
		${DESTDIR}${PREFIX}/include/ModemManager/
	sed -e 's|@VERSION@|1.22.0|' -e 's|@MM_MAJOR_VERSION@|1|' \
		-e 's|@MM_MINOR_VERSION@|22|' -e 's|@MM_MICRO_VERSION@|0|' \
		${WRKSRC}/include/ModemManager-version.h.in > \
		${DESTDIR}${PREFIX}/include/ModemManager/ModemManager-version.h
	/usr/bin/xsltproc --xinclude --nonet --output \
		${DESTDIR}${PREFIX}/include/ModemManager/ModemManager-names.h \
		${WRKSRC}/build-aux/header-generator.xsl ${WRKSRC}/introspection/all.xml
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/lib/pkgconfig
	{ echo 'prefix=/usr/pkg'; \
	  echo 'includedir=$${prefix}/include'; \
	  echo; \
	  echo 'Name: ModemManager'; \
	  echo 'Description: ModemManager DBus interface constants (headers only)'; \
	  echo 'Version: 1.22.0'; \
	  echo 'Cflags: -I$${includedir} -I$${includedir}/ModemManager'; \
	} > ${DESTDIR}${PREFIX}/lib/pkgconfig/ModemManager.pc

.include "../../mk/bsd.pkg.mk"
