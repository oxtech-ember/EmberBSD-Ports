# $NetBSD: Makefile,v 1.41 2022/02/17 15:42:00 wiz Exp $

DISTNAME=	findutils-4.11.0
PKGREVISION=	2
CATEGORIES=	sysutils
MASTER_SITES=	${MASTER_SITE_GNU:=findutils/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	bouyer@NetBSD.org
HOMEPAGE=	https://www.gnu.org/software/findutils/findutils.html
COMMENT=	find, locate, updatedb, and xargs utilities
LICENSE=	gnu-gpl-v3 # or later

GNU_CONFIGURE=		yes
INFO_FILES=		yes
USE_PKGLOCALEDIR=	yes
USE_TOOLS+=		gmake

LDFLAGS.IRIX+=		-lgen

CONFIGURE_ARGS+=	--program-prefix=g
CONFIGURE_ARGS+=	--localstatedir=/var/run

AUTO_MKDIRS=		yes

.if defined(EMBERBSD_DARWIN_UNAME)
CONFIGURE_ENV+=		EMBERBSD_CONFIGURE_SDK=yes
CONFIGURE_ENV+=		EMBERBSD_CONFIGURE_UNAME=${EMBERBSD_DARWIN_UNAME:Q}
.elif defined(EMBERBSD_GCC16_UNAME)
CONFIGURE_ENV+=		EMBERBSD_CONFIGURE_SDK=yes
CONFIGURE_ENV+=		EMBERBSD_CONFIGURE_UNAME=${EMBERBSD_GCC16_UNAME:Q}
.endif

post-extract:
	${CP} ${FILESDIR}/emberbsd-configure-diagnostics.sh ${WRKSRC}/

# The paired configure patch retains the released generator outputs.
pre-configure:
	${TOUCH} -r ${WRKSRC}/aclocal.m4 ${WRKSRC}/configure.ac

post-install:
.for f in find locate updatedb xargs
	${LN} -sf ${PREFIX}/bin/g${f} ${DESTDIR}${PREFIX}/${PKGGNUDIR}bin/${f}
	${LN} -sf ${PREFIX}/${PKGMANDIR}/man1/g${f}.1 ${DESTDIR}${PREFIX}/${PKGGNUDIR}${PKGMANDIR}/man1/${f}.1
.endfor
	${LN} -sf ${PREFIX}/${PKGMANDIR}/man5/glocatedb.5 ${DESTDIR}${PREFIX}/${PKGGNUDIR}${PKGMANDIR}/man5/locatedb.5

.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
