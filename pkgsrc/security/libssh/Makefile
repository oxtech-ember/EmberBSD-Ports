# $NetBSD: Makefile,v 1.61 2026/08/26 08:13:36 wiz Exp $

DISTNAME=	libssh-0.12.2
CATEGORIES=	security
MASTER_SITES=	https://www.libssh.org/files/${PKGVERSION_NOREV:R}/
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	is@NetBSD.org
HOMEPAGE=	https://www.libssh.org/
COMMENT=	SSHv2+v1 protocol library
LICENSE=	2-clause-bsd

USE_LANGUAGES=		c c++
PKGCONFIG_OVERRIDE+=	libssh.pc.cmake
TEST_TARGET=		test

CMAKE_CONFIGURE_ARGS+=	-DWITH_EXAMPLES=OFF

CFLAGS.SunOS+=		-D_POSIX_PTHREAD_SEMANTICS
LDFLAGS.SunOS+=		-lnsl -lsocket

BUILDLINK_TRANSFORM+=	rm:-Werror=strict-overflow

.include "options.mk"

.include "../../devel/cmake/build.mk"
.include "../../devel/zlib/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	3	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"
