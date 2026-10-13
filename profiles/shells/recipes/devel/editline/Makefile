# $NetBSD: Makefile,v 1.19 2025/06/01 14:42:23 vins Exp $

DISTNAME=	libedit-20260512-3.1
PKGNAME=	editline-3.1.20260512
CATEGORIES=	devel
MASTER_SITES=	https://thrysoee.dk/editline/

MAINTAINER=		ryoon@NetBSD.org
HOMEPAGE=		https://thrysoee.dk/editline/
COMMENT=		NetBSD Editline library (libedit) for generic line editing
LICENSE=		modified-bsd

PKGCONFIG_OVERRIDE+=	libedit.pc.in

USE_LIBTOOL=		yes
GNU_CONFIGURE=		yes
USE_LANGUAGES=		c c++
USE_TOOLS+=		autoconf automake autoreconf
GCC_REQD+=		16.2
BUILDLINK_API_DEPENDS.ncurses+=	ncurses>=6.6

post-install:
	# Install symlink like NetBSD base system has
	cd ${DESTDIR}${PREFIX}/include/editline && ln -sf readline.h history.h

.include "../../mk/bsd.prefs.mk"

pre-configure:
.if ${OPSYS} == "SunOS" && !exists(/usr/include/err.h)
	${CP} ${FILESDIR}/err.h ${BUILDLINK_DIR}/include
.endif
	cd ${WRKSRC} && autoreconf -fi

.include "../../devel/ncurses/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
