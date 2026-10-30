# $NetBSD: Makefile,v 1.31 2024/04/29 01:18:08 gutteridge Exp $

DISTNAME=	tcpreplay-4.4.4
CATEGORIES=	net
MASTER_SITES=	${MASTER_SITE_GITHUB:=appneta/}
GITHUB_RELEASE=	v${PKGVERSION_NOREV}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://tcpreplay.appneta.com/
COMMENT=	Replay saved tcpdump or snoop files
LICENSE=	gnu-gpl-v3

BUILDLINK_API_DEPENDS.libpcap+=	libpcap>=0.8.0

GNU_CONFIGURE=	yes
USE_LIBTOOL=	yes

CONFIGURE_ARGS+=	--enable-dynamic-link
CONFIGURE_ARGS+=	--with-libpcap=${BUILDLINK_PREFIX.libpcap}

do-test:
	cd ${WRKSRC}/test && ${SETENV} ${MAKE_ENV} ${MAKE} test

.include "../../net/libpcap/buildlink3.mk"
# EmberBSD cross addition: libopts is C++, and the recipe leaves
# USE_LANGUAGES unset so the wrappers refuse plain C entirely; set both.
# configure tests for the --with-libpcap headers and library with
# test -f on the build host, where /usr/pkg is not the target's; point it
# at the buildlink tree, which holds the target libpcap.
USE_LANGUAGES=	c c++
.  if ${USE_CROSS_COMPILE:U:tl} == "yes"
CONFIGURE_ARGS:=	${CONFIGURE_ARGS:N--with-libpcap=*}
CONFIGURE_ARGS+=	--with-libpcap=${BUILDLINK_DIR}
# libopts records the first bash on PATH (the host bootstrap one) and
# embeds it into every binary; the tools only need a POSIX shell.
CONFIGURE_ARGS+=	POSIX_SHELL=/bin/sh
.  endif

.include "../../mk/bsd.pkg.mk"
