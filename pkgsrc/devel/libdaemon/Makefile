# $NetBSD: Makefile,v 1.10 2021/11/29 16:31:57 jperkin Exp $
#

DISTNAME=		libdaemon-0.14
PKGREVISION=		3
CATEGORIES=		devel
MASTER_SITES=		https://0pointer.de/lennart/projects/libdaemon/

MAINTAINER=		pkgsrc-users@NetBSD.org
HOMEPAGE=		https://0pointer.de/lennart/projects/libdaemon/
COMMENT=		C library that eases the writing of UNIX daemons
LICENSE=		gnu-lgpl-v2.1

USE_PKGLOCALEDIR=	YES
USE_LIBTOOL=		YES
PKGCONFIG_OVERRIDE+=	pkgconfig/libdaemon.pc.in
GNU_CONFIGURE=		YES

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
# The target unistd.h declares BSD setpgrp(pid_t, pid_t).
CONFIGURE_ENV+= ac_cv_func_setpgrp_void=no
.endif

CONFIGURE_ARGS+=	--disable-lynx

INSTALLATION_DIRS=	share/doc/libdaemon

post-install:
	${INSTALL_DATA} ${WRKSRC}/doc/README ${DESTDIR}${PREFIX}/share/doc/libdaemon

.include "../../mk/bsd.pkg.mk"

.if (${OPSYS} == "NetBSD" && ${OPSYS_VERSION} < 050000) || ${OPSYS} == "OpenBSD"
BUILDLINK_TRANSFORM+=	rm:-Wl,--no-undefined
.endif
