# $NetBSD: Makefile,v 1.2 2026/05/27 17:15:13 kikadf Exp $
# Origin: pkgsrc, adapted by EmberBSD (AI-assisted).
# Headers only from the current libopeninput fork; no input runtime is built.
DISTNAME= libopeninput-1.31.3
PKGNAME= input-headers-1.31.3
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=sizeofvoid/}
GITHUB_PROJECT= libopeninput
GITHUB_TAG= 10995219206280da0f1a3ba124abe4c8ef89e021

MAINTAINER= kikadf@NetBSD.org
HOMEPAGE= https://github.com/sizeofvoid/libopeninput/tree/libopeninput/
COMMENT= Input headers from libopeninput
LICENSE= mit
USE_LANGUAGES= # none
USE_TOOLS+= pax
INSTALLATION_DIRS+= include/linux

do-configure:

do-build:

do-install:
	${RUN} cd ${WRKSRC}/include/linux && \
		${FIND} . -type f -name "*.h" -print | pax -rw -pmp ${DESTDIR}${PREFIX}/include/linux

.include "../../mk/bsd.pkg.mk"
