# $NetBSD: Makefile,v 1.15 2022/06/28 11:34:58 wiz Exp $
#

DISTNAME=	arp-scan-1.9
PKGREVISION=	7
CATEGORIES=	net
MASTER_SITES=	http://www.nta-monitor.com/files/arp-scan/

MAINTAINER=	pkgsrc-users@NetBSD.org
#HOMEPAGE=	http://www.nta-monitor.com/tools-resources/security-tools/arp-scan
COMMENT=	Discovery and fingerprinting tool using ARP
LICENSE=	gnu-gpl-v3

GNU_CONFIGURE=	yes
USE_TOOLS+=	perl:run

REPLACE_PERL=	arp-fingerprint get-iab get-oui

BUILDLINK_API_DEPENDS.libpcap+=	libpcap>=0.8
.include "../../net/libpcap/buildlink3.mk"

# EmberBSD cross addition: the package ships perl helper scripts
# (arp-fingerprint) whose :run tool is not a NetBSD base utility and
# stays unsupported in cross builds. Keep the C arp-scan tool and drop
# the perl helpers from the board kit.
.  if ${USE_CROSS_COMPILE:U:tl} == "yes"
USE_TOOLS:=	${USE_TOOLS:Nperl\:run}
REPLACE_PERL=	# none
PLIST_VARS+=	emberperl
# The bundled gnulib getopt.h re-declares getopt (and via it getenv)
# without prototypes and conflicts with the NetBSD system declarations.
# NetBSD provides getopt.h itself, so drop the bundled copy and build
# against the system header.
post-extract:
	${RM} -f ${WRKSRC}/getopt.h

ember-remove-perl-helpers:
	${RM} -f ${DESTDIR}${PREFIX}/bin/arp-fingerprint \
	    ${DESTDIR}${PREFIX}/bin/get-iab ${DESTDIR}${PREFIX}/bin/get-oui \
	    ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/get-iab.1 \
	    ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/get-oui.1 \
	    ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/arp-fingerprint.1
post-install: ember-remove-perl-helpers
.  else
PLIST.emberperl=	yes
.  endif

.include "../../mk/bsd.pkg.mk"
