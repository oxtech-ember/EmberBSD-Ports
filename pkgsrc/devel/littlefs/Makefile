# Origin: littlefs-project/littlefs v2.11.3; source-only shared owner.
DISTNAME=	littlefs-2.11.3
PKGNAME=	littlefs-source-2.11.3
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=littlefs-project/}
GITHUB_PROJECT=	littlefs
GITHUB_TAG=	refs/tags/v2.11.3
EXTRACT_SUFX=	.tar.gz
WRKSRC=	${WRKDIR}/littlefs-2.11.3

HOMEPAGE=	https://github.com/littlefs-project/littlefs
COMMENT=	Shared upstream littlefs source for OS and image-builder consumers
LICENSE=	3-clause-bsd

NO_ARCH=	yes
NO_BUILD=	yes
NO_CONFIGURE=	yes
USE_LANGUAGES=	# source only
USE_TOOLS+=	find sort tar

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/littlefs-source
	${TAR} -cf ${WRKDIR:Q}/littlefs-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/littlefs-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/littlefs-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/littlefs-source \( -type f -o -type l \) -print | ${SORT};

.include "../../mk/bsd.pkg.mk"
