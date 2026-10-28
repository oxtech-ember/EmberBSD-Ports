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
BUILDLINK_API_DEPENDS.ncurses+=	ncurses>=6.6

post-install:
	# Install symlink like NetBSD base system has
	cd ${DESTDIR}${PREFIX}/include/editline && ln -sf readline.h history.h

.include "../../mk/bsd.prefs.mk"

# EmberBSD deploys this source through the native base library.
# Direct package builds must not install a second portable provider.
.if (${OPSYS} == "NetBSD" && (${EMBERBSD_PORTS:Uno:tl} == "yes" || \
    exists(${.PARSEDIR}/../../EMBERBSD-PKGSRC-REVISION))) || \
    exists(${TOOLS_CROSS_DESTDIR}/usr/share/emberbsd/ports/editline.distinfo)
PKG_FAIL_REASON+= "EmberBSD base provides libedit. Rebuild the base through the SDK instead of installing this package."
.endif

pre-configure:
.if ${OPSYS} == "SunOS" && !exists(/usr/include/err.h)
	${CP} ${FILESDIR}/err.h ${BUILDLINK_DIR}/include
.endif
	cd ${WRKSRC} && autoreconf -fi

.include "../../devel/ncurses/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
