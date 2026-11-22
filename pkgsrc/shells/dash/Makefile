# $NetBSD: Makefile,v 1.21 2026/07/22 07:32:51 adam Exp $

DISTNAME=	dash-0.5.13.6
CATEGORIES=	shells
MASTER_SITES=	https://git.kernel.org/pub/scm/utils/dash/dash.git/snapshot/

MAINTAINER=	cheusov@NetBSD.org
HOMEPAGE=	https://git.kernel.org/pub/scm/utils/dash/dash.git/
COMMENT=	Debian Almquist shell, POSIX-compliant shell faster than bash
LICENSE=	modified-bsd AND gnu-gpl-v2

USE_TOOLS+=		autoconf automake aclocal autoheader gmake
GNU_CONFIGURE=		yes
CONFIGURE_ARGS+=	--with-libedit
PKG_SHELL=		bin/dash

# Needed after patching configure.ac.
pre-configure:
	cd ${WRKSRC} && autoreconf -fiv

.include "../../devel/editline/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
