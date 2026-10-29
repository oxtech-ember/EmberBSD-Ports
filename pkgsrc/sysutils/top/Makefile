# $NetBSD$

DISTNAME=	top-3.8beta1
CATEGORIES=	sysutils
MASTER_SITES=	https://downloads.sourceforge.net/project/unixtop/unixtop/top-3.8beta1/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://unixtop.sourceforge.net/
COMMENT=	System and process monitor
LICENSE=	modified-bsd

GNU_CONFIGURE=	yes
BUILD_TARGET=	top
USE_TOOLS+=	awk
PATCH_STRIP=	-p1
INSTALLATION_DIRS+=	share/doc/top
CONFIGURE_ENV+=	SET_OWNER=${BINOWN} SET_GROUP=${BINGRP} SET_MODE=${BINMODE}

# The Darwin backend requires the removed kvm interfaces.
BROKEN_ON_PLATFORM+=	Darwin-9.*-* Darwin-[1-9][0-9]*-*
CONFIGURE_ARGS.Darwin+=	--with-module=macosx

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "NetBSD"
LIBS+=	-lutil
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if !defined(TOP_TARGET_MACHINE) && defined(EMBERBSD_SDK_SOURCE) && defined(EMBERBSD_CROSS_TARGET)
TOP_TARGET_MACHINE!=	${EMBERBSD_HOST_PYTHON:Q} -B -E -S ${FILESDIR:Q}/target-machine.py ${EMBERBSD_SDK_SOURCE:Q} ${EMBERBSD_CROSS_TARGET:Q}
.endif
TOP_TARGET_MACHINE?=
CONFIGURE_ENV+=	TOP_TARGET_MACHINE=${TOP_TARGET_MACHINE:Q} TOP_TARGET_OSVERSION=${OS_VERSION:Q}
CONFIGURE_ENV+=	TOP_TARGET_SYSROOT=${CROSS_DESTDIR:Q}
.if ${OPSYS} == "NetBSD"
CONFIGURE_ENV+=	SIGNAL_H=${CROSS_DESTDIR:Q}/usr/include/sys/signal.h
.endif
.endif

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/doc/top/LICENSE

.include "../../mk/termcap.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
