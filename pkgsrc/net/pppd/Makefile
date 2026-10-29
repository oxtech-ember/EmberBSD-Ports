# $NetBSD$

DISTNAME=	ppp-2.5.4
PKGREVISION=	2
PKGNAME=	${DISTNAME:S/ppp/pppd/}
CATEGORIES=	net
MASTER_SITES=	https://www.samba.org/ftp/ppp/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://ppp.samba.org/
COMMENT=	Point-to-point protocol daemon and utilities
# Individual source notices include CMU attribution and GPL plugin terms.
LICENSE=	ppp-cmu AND ppp-attribution AND 2-clause-bsd AND \
		modified-bsd AND gnu-gpl-v2

ONLY_FOR_PLATFORM+=	SunOS-*-* Linux-*-* NetBSD-*-* DragonFly-*-*
GNU_CONFIGURE=	yes
USE_LIBTOOL=	yes
# The base libpcap source is not yet equivalent to the common recipe.
USE_BUILTIN.libpcap=	no
USE_TOOLS+=	autoconf automake autoreconf gmake pkg-config
PATCH_STRIP=	-p1
CONFIGURE_ARGS+=	--disable-maintainer-mode --enable-multilink
CONFIGURE_ARGS+=	--enable-cbcp --enable-mslanman
CONFIGURE_ARGS+=	--sysconfdir=${PKG_SYSCONFDIR:Q}
PKG_SYSCONFSUBDIR=	ppp
EGDIR=		${PREFIX}/share/examples
INSTALL_MAKE_FLAGS+=	sysconfdir=${EGDIR:Q}

pre-configure:
	cd ${WRKSRC} && ${SETENV} ${CONFIGURE_ENV} autoreconf -fi

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/doc/pppd
	${INSTALL_DATA} ${FILESDIR}/NOTICES ${DESTDIR}${PREFIX}/share/doc/pppd/NOTICES
	${INSTALL_DATA} ${WRKSRC}/COPYING ${DESTDIR}${PREFIX}/share/doc/pppd/COPYING
	${INSTALL_DATA} ${WRKSRC}/LICENSE.BSD ${DESTDIR}${PREFIX}/share/doc/pppd/LICENSE.BSD
	${INSTALL_DATA} ${WRKSRC}/LICENSE.GPL-2 ${DESTDIR}${PREFIX}/share/doc/pppd/LICENSE.GPL-2

.include "../../databases/tdb/buildlink3.mk"
.include "../../net/libpcap/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
