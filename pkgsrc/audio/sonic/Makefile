# $NetBSD: Makefile,v 1.1 2024/01/30 09:00:40 wiz Exp $

# No newer upstream release exists; pin the maintained 2026 source snapshot.
DISTNAME=	sonic-0.3.0.20260314
CATEGORIES=	audio
MASTER_SITES=	${MASTER_SITE_GITHUB:=waywardgeek/}
GITHUB_TAG=	b93885dcb70aae50c6f76b0fe4e0868f029a077e

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/waywardgeek/sonic
COMMENT=	Simple library to speed up or slow down speech
LICENSE=	apache-2.0

USE_LANGUAGES=		c
USE_TOOLS=		gmake
CFLAGS+=		-Wall -Wno-unused-function -ansi -fPIC -pthread
CFLAGS+=		${COMPILER_RPATH_FLAG}${PREFIX}/lib
MAKE_FLAGS+=		PREFIX=${PREFIX}
# Upstream's uname describes the host, not the cross-built shared library.
MAKE_FLAGS+=		UNAME=${OPSYS} CC=${CC:Q} AR=${AR:Q} CFLAGS=${CFLAGS:Q}

.include "../../mk/bsd.pkg.mk"
