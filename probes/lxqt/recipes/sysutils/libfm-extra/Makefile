# $NetBSD: Makefile,v 1.23 2026/09/02 19:04:31 wiz Exp $

DISTNAME=	libfm-1.4.1
PKGNAME=	libfm-extra-1.4.1
CATEGORIES=	sysutils
MASTER_SITES=	https://raw.githubusercontent.com/lxde/releases/5226c729f1f5cf5f7e78b3574a36b4818bcafb8d/releases/
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://sourceforge.net/projects/pcmanfm/
COMMENT=	File management library (extra)
LICENSE=	gnu-lgpl-v2.1

GNU_CONFIGURE=		yes
USE_LIBTOOL=		yes
USE_TOOLS+=		intltool pkg-config msgfmt

CONFIGURE_ARGS+=	--with-extra-only
INSTALLATION_DIRS=	include/libfm

# XXX: walk-around bug in build wrappers
#      they try to copy $PREFIX/include/libfm to work dir and there link libfm -> libfm-1.0 is resolved
#      in the end a consumer of libfm cannot find nonexisting include/libfm
post-install:
	${RUN} ${RM} -f ${DESTDIR}${PREFIX}/include/libfm
	${RUN} ${CP} -r ${DESTDIR}${PREFIX}/include/libfm-1.0 ${DESTDIR}${PREFIX}/include/libfm

.include "../../devel/glib2/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
