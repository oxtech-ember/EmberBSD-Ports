# $NetBSD: Makefile,v 1.20 2026/08/04 20:28:50 wiz Exp $
#

DISTNAME=	hfsutils-3.2.6
PKGNAME=	libhfs-3.2.6
PKGREVISION=	3
CATEGORIES=	devel sysutils
MASTER_SITES=	ftp://ftp.mars.org/pub/hfs/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.mars.org/home/rob/proj/hfs/
COMMENT=	Library for accessing HFS (Apple Macintosh) volumes
LICENSE=	gnu-gpl-v2

GNU_CONFIGURE=	yes
USE_LIBTOOL=	yes
BUILD_TARGET=	all_lib

CPPFLAGS=	-I.

INSTALLATION_DIRS=	lib

pre-patch:
	for f in librsrc/librsrc.h libhfs/libhfs.h; do \
	  ${MV} ${WRKSRC}/$$f ${WRKSRC}/$$f-prepatch; \
	  ${SED} -e '/Id/s|\$$||g' ${WRKSRC}/$$f-prepatch > ${WRKSRC}/$$f; \
	done

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/include/libhfs
	cd ${WRKSRC}/libhfs; \
	  ${LIBTOOL} --mode=install ${INSTALL_PROGRAM} libhfs.la \
		${DESTDIR}${PREFIX}/lib; \
	  ${INSTALL_DATA} apple.h data.h hfs.h libhfs.h \
		${DESTDIR}${PREFIX}/include/libhfs
	cd ${WRKSRC}/librsrc; \
	  ${LIBTOOL} --mode=install ${INSTALL_PROGRAM} librsrc.la \
		${DESTDIR}${PREFIX}/lib; \
	  ${INSTALL_DATA} librsrc.h rsrc.h ${DESTDIR}${PREFIX}/include/libhfs
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/doc/libhfs
	cd ${WRKSRC}/doc; ${INSTALL_DATA} charset.txt libhfs.txt librsrc.txt \
	  ${DESTDIR}${PREFIX}/share/doc/libhfs
	${INSTALL_DATA} ${WRKSRC}/COPYING ${WRKSRC}/COPYRIGHT ${DESTDIR}${PREFIX}/share/doc/libhfs

# The compiler wrappers add the RELRO flags to links themselves. Adding them
# to every compiler run makes Clang warn on preprocessor runs, and the old
# configure script then rejects the preprocessor and every header check.

.include "../../mk/bsd.pkg.mk"
