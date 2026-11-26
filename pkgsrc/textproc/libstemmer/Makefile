# $NetBSD: Makefile,v 1.8 2023/07/13 06:21:47 nia Exp $

DISTNAME=	libstemmer_c-3.2.0
PKGNAME=	${DISTNAME:S/libstemmer_c/libstemmer/}
PKGREVISION=	1
CATEGORIES=	textproc
MASTER_SITES=	https://snowballstem.org/dist/

MAINTAINER=	ryoon@NetBSD.org
HOMEPAGE=	https://snowballstem.org/
COMMENT=	Snowball stemming algorithms for C
LICENSE=	modified-bsd

USE_TOOLS+=	gmake
USE_LIBTOOL=	yes
BUILD_TARGET=	libstemmer.la

INSTALLATION_DIRS+=	include lib

do-install:
	${INSTALL_DATA} ${WRKSRC}/include/libstemmer.h \
	    ${DESTDIR}${PREFIX}/include
	${LIBTOOL} --quiet --tag=CC --mode=install \
	    ${INSTALL_LIB} ${WRKSRC}/libstemmer.la ${DESTDIR}${PREFIX}/lib

.include "../../mk/bsd.pkg.mk"
