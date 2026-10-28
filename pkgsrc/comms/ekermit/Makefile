# $NetBSD$
# Origin: EmberBSD (AI-assisted); shared E-Kermit source and Unix program.

DISTNAME=       ekermit-1.8
DISTFILES=      ek18.tar
EXTRACT_SUFX=   .tar
MASTER_SITES=   https://www.kermitproject.org/ftp/kermit/archives/
CATEGORIES=     comms
MAINTAINER=     pkgsrc-users@NetBSD.org
HOMEPAGE=       https://www.kermitproject.org/ek.html
COMMENT=        Embedded Kermit protocol and Unix sample program
LICENSE=        modified-bsd

WRKSRC=         ${WRKDIR}
MAKE_FILE=      makefile
BUILD_TARGET=   ek
MAKE_FLAGS+=    CC=${CC:Q} CFLAGS=${CFLAGS:Q} LDFLAGS=${LDFLAGS:Q}
INSTALLATION_DIRS= bin

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/ek ${DESTDIR}${PREFIX}/bin/ekermit

.include "../../mk/bsd.pkg.mk"
