# $NetBSD$

DISTNAME=	ptpd-2.3.1
PKGREVISION=	1
CATEGORIES=	net time
MASTER_SITES=	${MASTER_SITE_GITHUB:=ptpd/}
# The 2.3.1 branch head, with the hash recorded by FreeBSD net/ptpd2.
GITHUB_TAG=	d27a6e0
WRKSRC=		${WRKDIR}/ptpd-${GITHUB_TAG}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/ptpd/ptpd
COMMENT=	Precision Time Protocol (IEEE 1588-2008) daemon
LICENSE=	2-clause-bsd

GNU_CONFIGURE=	yes
USE_TOOLS+=	autoconf automake autoreconf gmake pkg-config
USE_LIBTOOL=	yes
USE_LANGUAGES=	c

# Net-SNMP is a separate integration; the daemon keeps its own statistics.
CONFIGURE_ARGS+=	--disable-snmp

RCD_SCRIPTS=		ptpd2

pre-configure:
	cd ${WRKSRC} && autoreconf -fi

.include "../../mk/bsd.pkg.mk"
