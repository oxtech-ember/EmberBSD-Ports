# Common patched zlib sources for freestanding consumers.
.include "../../devel/zlib/Makefile.common"

DISTNAME= zlib-${ZLIB_VERSION}
PKGNAME= zlib-source-${ZLIB_VERSION}
PKGREVISION= ${ZLIB_PATCH_REVISION}
CATEGORIES= devel
MASTER_SITES= https://zlib.net/
EXTRACT_SUFX= .tar.xz
DISTINFO_FILE= ${.CURDIR}/../../devel/zlib/distinfo
PATCHDIR= ${.CURDIR}/../../devel/zlib/patches

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://www.zlib.net/
COMMENT= Common patched zlib source for freestanding consumers
LICENSE= zlib

USE_LANGUAGES= # none
NO_CONFIGURE= yes
NO_BUILD= yes
INSTALLATION_DIRS+= share/zlib-source/core

ZLIB_SOURCE_FILES= LICENSE README adler32.c compress.c crc32.c crc32.h \
 deflate.c deflate.h gzclose.c gzguts.h gzlib.c gzread.c gzwrite.c \
 infback.c inffast.c inffast.h inffixed.h inflate.c inflate.h \
 inftrees.c inftrees.h trees.c trees.h uncompr.c zconf.h zlib.h zutil.c zutil.h

do-install:
.for file in ${ZLIB_SOURCE_FILES}
	${INSTALL_DATA} ${WRKSRC}/${file} ${DESTDIR}${PREFIX}/share/zlib-source/core/${file}
.endfor

.include "../../mk/bsd.pkg.mk"
