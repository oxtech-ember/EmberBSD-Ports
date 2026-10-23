# Origin: EmberBSD (AI-assisted). Header-only extraction; NetworkManagerQt
# needs only the public libnm headers and their DBus constants, no daemon
# and no client library. The three linux/ shims supply the few kernel
# constants the public headers reference.

DISTNAME=	NetworkManager-1.52.0
PKGNAME=	networkmanager-headers-1.52.0
CATEGORIES=	net
MASTER_SITES=	https://gitlab.freedesktop.org/NetworkManager/NetworkManager/-/archive/1.52.0/
EXTRACT_SUFX=	.tar.gz

HOMEPAGE=	https://networkmanager.dev/
COMMENT=	NetworkManager public libnm headers (header-only)
LICENSE=	gnu-lgpl-v2.1

WRKSRC=		${WRKDIR}/NetworkManager-1.52.0
NO_BUILD=	yes
USE_LANGUAGES=	# none
CHECK_PORTABILITY_SKIP=	contrib/scripts/*

# The public headers carry a generated version-macros header and a
# glib-mkenums enum-types header; both are produced on the build host.
do-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/include/libnm
	${INSTALL_DATA} ${WRKSRC}/src/libnm-client-public/*.h \
		${DESTDIR}${PREFIX}/include/libnm/
	${INSTALL_DATA} ${WRKSRC}/src/libnm-core-public/*.h \
		${DESTDIR}${PREFIX}/include/libnm/
	${RM} -f ${DESTDIR}${PREFIX}/include/libnm/*.template
	sed -e 's|@NM_MAJOR_VERSION@|1|' -e 's|@NM_MINOR_VERSION@|52|' \
		-e 's|@NM_MICRO_VERSION@|0|' -e 's|@NM_VERSION@|15200|' \
		${WRKSRC}/src/libnm-core-public/nm-version-macros.h.in > \
		${DESTDIR}${PREFIX}/include/libnm/nm-version-macros.h
	/opt/homebrew/bin/glib-mkenums --identifier-prefix NM --symbol-prefix nm \
		--template ${WRKSRC}/src/libnm-client-public/nm-enum-types.h.template \
		${WRKSRC}/src/libnm-client-public/*.h ${WRKSRC}/src/libnm-core-public/*.h \
		> ${DESTDIR}${PREFIX}/include/libnm/nm-core-enum-types.h
	${CP} ${DESTDIR}${PREFIX}/include/libnm/nm-core-enum-types.h \
		${DESTDIR}${PREFIX}/include/libnm/nm-enum-types.h
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/include/linux
	${INSTALL_DATA} ${FILESDIR}/if_ether.h ${FILESDIR}/if_infiniband.h \
		${FILESDIR}/if_vlan.h ${DESTDIR}${PREFIX}/include/linux/
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/lib/pkgconfig
	{ echo 'prefix=/usr/pkg'; \
	  echo 'includedir=$${prefix}/include'; \
	  echo; \
	  echo 'Name: libnm'; \
	  echo 'Description: NetworkManager public headers (header only)'; \
	  echo 'Version: 1.52.0'; \
	  echo 'Requires: gio-2.0'; \
	  echo 'Cflags: -I$${includedir} -I$${includedir}/libnm'; \
	} > ${DESTDIR}${PREFIX}/lib/pkgconfig/libnm.pc

.include "../../mk/bsd.pkg.mk"
