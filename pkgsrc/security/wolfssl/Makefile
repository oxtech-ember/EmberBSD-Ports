# $NetBSD: Makefile,v 1.32 2026/06/27 08:23:26 fox Exp $

DISTNAME=	wolfssl-5.9.4
CATEGORIES=	security
MASTER_SITES=	https://www.wolfssl.com/
EXTRACT_SUFX=	.zip
PKGREVISION=	2

MAINTAINER=	fox@NetBSD.org
HOMEPAGE=	https://www.wolfssl.com/
COMMENT=	Embedded SSL C-Library
LICENSE=	gnu-gpl-v3
USE_LANGUAGES=	c

PKG_OPTIONS_VAR=	PKG_OPTIONS.wolfssl
PKG_SUPPORTED_OPTIONS=	shared tests
PKG_SUGGESTED_OPTIONS=	shared tests
.include "../../mk/bsd.options.mk"

GNU_CONFIGURE=		yes
CONFIGURE_ARGS+=	--disable-dependency-tracking
# The upstream examples and crypt tests are not installed by this package.
# Default to the package's prior test coverage; cross consumers can opt out.
.if !empty(PKG_OPTIONS:Mtests)
CONFIGURE_ARGS+=	--enable-examples
CONFIGURE_ARGS+=	--enable-crypttests
TEST_TARGET=	check
.else
CONFIGURE_ARGS+=	--disable-examples
CONFIGURE_ARGS+=	--disable-crypttests
.PHONY: do-test
do-test:
	@${ECHO_MSG} "WolfSSL tests are disabled; set PKG_OPTIONS.wolfssl=tests to run them"
	@${FALSE}
.endif
CONFIGURE_ARGS+=	--enable-dh
CONFIGURE_ARGS+=	--enable-dsa
CONFIGURE_ARGS+=	--enable-dtls
CONFIGURE_ARGS+=	--enable-ecc
CONFIGURE_ARGS+=	--enable-ipv6
CONFIGURE_ARGS+=	--enable-keygen
CONFIGURE_ARGS+=	--enable-opensslextra
CONFIGURE_ARGS+=	--enable-wpas
CONFIGURE_ARGS+=	--enable-ripemd
CONFIGURE_ARGS+=	--enable-sha512
.if !empty(PKG_OPTIONS:Mshared)
CONFIGURE_ARGS+=	--enable-shared
.else
CONFIGURE_ARGS+=	--disable-shared
.endif
CONFIGURE_ARGS+=	--enable-sni
CONFIGURE_ARGS+=	--enable-ssh
CONFIGURE_ARGS+=	--enable-static
CONFIGURE_ARGS+=	--enable-tls13
CONFIGURE_ARGS+=	--enable-tls13-draft18

PKGCONFIG_OVERRIDE+=	support/wolfssl.pc.in

USE_LIBTOOL=	yes

# XXX: Mutex related test fails with error -9906 in NetBSD 7/8/9 but
# this has been fixed in -current, libpthread in 9.99.46 
.include "../../mk/bsd.pkg.mk"
