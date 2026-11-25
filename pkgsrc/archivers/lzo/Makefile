# $NetBSD: Makefile,v 1.19 2020/01/26 17:30:40 rillig Exp $

DISTNAME=	lzo-2.10
PKGREVISION=	2
CATEGORIES=	archivers
MASTER_SITES=	https://www.oberhumer.com/opensource/lzo/download/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.oberhumer.com/opensource/lzo/
COMMENT=	Portable lossless data compression library
LICENSE=	gnu-gpl-v2

USE_LIBTOOL=		yes
GNU_CONFIGURE=		yes
TEST_TARGET=		test
PKGCONFIG_OVERRIDE=	lzo2.pc.in

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && \
    (${MACHINE_ARCH} == "aarch64" || ${MACHINE_ARCH} == "x86_64")
PKGREVISION=	3	# Record the base libc SONAME.
.endif

.include "../../mk/bsd.pkg.mk"
