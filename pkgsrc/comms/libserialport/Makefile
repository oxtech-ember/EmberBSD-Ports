# $NetBSD$
#
# EmberBSD port: libserialport 0.1.2 (sigrok), first pkgsrc recipe for
# the diagnostics kit (R10 stage three). Upstream has no pkgsrc package.

DISTNAME=	libserialport-0.1.2
CATEGORIES=	comms
MASTER_SITES=	https://sigrok.org/download/source/libserialport/
# Fedora keeps the same upstream archive under its SHA512 in distinfo.
MASTER_SITES+=	https://src.fedoraproject.org/repo/pkgs/libserialport/${DISTNAME}${EXTRACT_SUFX}/sha512/960823ddb30711c39a4f001b6dd2d592a072e8d4256d3ba0a2fdb6c28172c3b6b1504b33cca80765ded5d5add34a73621b5e500ebaa6bb0520faf98b46b903aa/
EXTRACT_SUFX=	.tar.gz

MAINTAINER=	ports@emberbsd.invalid
HOMEPAGE=	https://sigrok.org/wiki/Libserialport
COMMENT=	Minimal cross-platform serial port handling library
LICENSE=	gnu-lgpl-v3

GNU_CONFIGURE=	yes
USE_LIBTOOL=	yes
USE_TOOLS+=	pkg-config

.include "../../mk/bsd.pkg.mk"
