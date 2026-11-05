# $NetBSD: Makefile,v 1.2 2025/11/06 16:13:24 adam Exp $

.include "../../databases/sqlite3/Makefile.common"

# Shared source checksums and complete patch set belong to sqlite3.
DISTINFO_FILE=	${.CURDIR}/../../databases/sqlite3/distinfo
PATCHDIR=	${.CURDIR}/../../databases/sqlite3/patches

DISTNAME=	sqlite-src-${SQLITE3_DISTVERSION}
PKGNAME=	sqlite3-diff-${SQLITE3_VERSION}
PKGREVISION=	1
CATEGORIES=	databases
EXTRACT_SUFX=	.zip

MAINTAINER=	schmonz@NetBSD.org
COMMENT=	Display content differences between SQLite databases

HAS_CONFIGURE=	yes
USE_TOOLS+=	gmake
.include "../../mk/bsd.prefs.mk"
.include "../../databases/sqlite3/cross.mk"

BUILD_TARGET=	sqldiff

INSTALLATION_DIRS=	bin

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/sqldiff ${DESTDIR}${PREFIX}/bin

.include "../../mk/bsd.pkg.mk"
