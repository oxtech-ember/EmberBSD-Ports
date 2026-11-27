# $NetBSD: Makefile,v 1.32.2.2 2026/11/11 20:32:12 maya Exp $

DISTNAME=	wireguard-go-0.0.20250522
# Common handshake and IPv6 receive fixes; NetBSD TUN shutdown repair.
PKGREVISION=	20
CATEGORIES=	net
MASTER_SITES=	https://git.zx2c4.com/wireguard-go/snapshot/
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://git.zx2c4.com/wireguard-go/about/
COMMENT=	Implementation of WireGuard in Go
LICENSE=	mit

INSTALLATION_DIRS+=	bin

# Cross builds place the binary under bin/${GO_PLATFORM}.
do-install:
	${INSTALL_PROGRAM} ${WRKDIR}/.gopath/${GOPATH_BIN}/wireguard \
		${DESTDIR}${PREFIX}/bin/wireguard-go

GO_BUILD_PATTERN=	.

pre-patch:
	cd ${WRKSRC}/tun && ${LN} tun_openbsd.go tun_netbsd.go

post-patch:
	${CP} ${FILESDIR}/tun_close_netbsd_test.go ${WRKSRC}/tun/

.include "go-modules.mk"

.include "../../lang/go/go-module.mk"
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "aarch64"
PKGREVISION=	21	# Reissue the withdrawn AArch64 package.
.endif
.include "../../mk/bsd.pkg.mk"
