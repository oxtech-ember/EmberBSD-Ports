# $NetBSD: Makefile,v 1.68.2.1 2026/10/01 18:53:09 bsiegert Exp $

DISTNAME=	expat-2.10.0
PKGREVISION=	1
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=libexpat/}
GITHUB_PROJECT=	libexpat
GITHUB_RELEASE=	R_${PKGVERSION_NOREV:S/./_/g}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://libexpat.github.io/
COMMENT=	XML parser library written in C
LICENSE=	mit

USE_LANGUAGES=		c c++
USE_LIBTOOL=		yes
USE_TOOLS+=		bash:test
GNU_CONFIGURE=		yes
CONFIGURE_ARGS+=	--without-docbook
# workaround suggested by upstream; xmlwf.1 is in tarball, so docbook not needed
CONFIGURE_ENV+=		DOCBOOK_TO_MAN=false

TEST_TARGET=	check
REPLACE_BASH=	test-driver-wrapper.sh
# we can't use cmake due to a cyclic dependency
#USE_CMAKE=	yes

PKGCONFIG_OVERRIDE+=	expat.pc.in

DOCDIR=	${PREFIX}/share/doc/expat

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${DOCDIR}
	${INSTALL_DATA} ${WRKSRC}/doc/reference.html ${DESTDIR}${DOCDIR}
	${INSTALL_DATA} ${WRKSRC}/doc/style.css ${DESTDIR}${DOCDIR}

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
.  if ${MACHINE_ARCH} == "aarch64"
PKGREVISION=	3	# Rebuild with public host metadata.
.  elif ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	2	# Record the base libc SONAME.
.  endif
.endif

.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PKGREVISION=	2	# Rebuild native package with portable provenance.
.endif

.include "../../mk/bsd.pkg.mk"
