# $NetBSD: Makefile,v 1.15 2024/06/13 13:06:54 jperkin Exp $

DISTNAME=	flite-2.2
PKGREVISION=	3
CATEGORIES=	audio
MASTER_SITES=	${MASTER_SITE_GITHUB:=festvox/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	http://www.festvox.org/flite/
COMMENT=	Lightweight text to speech synthesis engine
LICENSE=	modified-bsd AND zlib

# Error opening output file '[...]/cmu_us_kal_diphone.o': No such file or directory
MAKE_JOBS_SAFE=	no

USE_TOOLS+=	gmake
GNU_CONFIGURE=	yes

CFLAGS.SunOS+=	-fPIC
LDFLAGS.SunOS+=	-lsocket -lnsl

.include "../../mk/bsd.prefs.mk"
PLIST_VARS+= shared
.if ${OPSYS} == "NetBSD"
# Qt discovers voices as shared libraries; keep the existing static libraries.
CONFIGURE_ARGS+= --enable-shared
MAKE_FLAGS+= SHFLAGS=-fPIC
PLIST.shared= yes
.endif

INSTALLATION_DIRS+=	bin include/flite lib share/doc/flite

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/bin/flite ${DESTDIR}${PREFIX}/bin
	${INSTALL_PROGRAM} ${WRKSRC}/bin/flite_cmu* ${DESTDIR}${PREFIX}/bin
	${INSTALL_PROGRAM} ${WRKSRC}/bin/flite_time ${DESTDIR}${PREFIX}/bin
	${CP} -P ${WRKSRC}/build/platform/lib/libflite* ${DESTDIR}${PREFIX}/lib
	${INSTALL_DATA} ${WRKSRC}/include/*.h ${DESTDIR}${PREFIX}/include/flite
	${INSTALL_DATA} ${WRKSRC}/README.md ${DESTDIR}${PREFIX}/share/doc/flite

.include "../../mk/bsd.pkg.mk"
