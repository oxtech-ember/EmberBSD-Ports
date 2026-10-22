# $NetBSD$
#
# EmberBSD port: libserialport 0.1.2 (sigrok), first pkgsrc recipe for
# the diagnostics kit (R10 stage three). Upstream has no pkgsrc package.

DISTNAME=	libserialport-0.1.2
CATEGORIES=	comms
MASTER_SITES=	https://sigrok.org/download/source/libserialport/
EXTRACT_SUFX=	.tar.gz

MAINTAINER=	ports@emberbsd.invalid
HOMEPAGE=	https://sigrok.org/wiki/Libserialport
COMMENT=	Minimal cross-platform serial port handling library
LICENSE=	gnu-lgpl-v3

GNU_CONFIGURE=	yes
USE_LIBTOOL=	yes
USE_TOOLS+=	pkg-config

.include "../../mk/bsd.pkg.mk"
