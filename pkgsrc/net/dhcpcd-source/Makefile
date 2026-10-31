.include "../../net/dhcpcd/Makefile.common"
PKGREVISION=	1

PKGNAME=	dhcpcd-source-${DHCPCD_VERSION}
CATEGORIES=	net
HOMEPAGE=	https://roy.marples.name/projects/dhcpcd/
COMMENT=	Prepared dhcpcd source with the common Ports patchset
LICENSE=	modified-bsd

DISTINFO_FILE=	${.CURDIR}/../../net/dhcpcd/distinfo
PATCHDIR=	${.CURDIR}/../../net/dhcpcd/patches
NO_ARCH=	yes
NO_BUILD=	yes
NO_CONFIGURE=	yes
USE_LANGUAGES=	# source only
USE_TOOLS+=	find sort
INSTALLATION_DIRS=	share/dhcpcd-source

do-install:
	${CP} -R ${WRKSRC}/. ${DESTDIR}${PREFIX}/share/dhcpcd-source/
	${FIND} ${DESTDIR}${PREFIX}/share/dhcpcd-source -name '*.orig' -exec ${RM} {} +
	${INSTALL_DATA} ${.CURDIR}/README.md ${DESTDIR}${PREFIX}/share/dhcpcd-source/README.EmberBSD.md

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/dhcpcd-source \( -type f -o -type l \) -print | ${SORT};
CHECK_INTERPRETER_SKIP+= share/dhcpcd-source/*
.include "../../mk/bsd.pkg.mk"
