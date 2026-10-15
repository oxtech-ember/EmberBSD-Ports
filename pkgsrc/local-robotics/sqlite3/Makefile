# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), current shared SQLite source package.
DISTNAME= sqlite-autoconf-3540000
PKGNAME= sqlite3-3.54.0
CATEGORIES= databases
MASTER_SITES= https://www.sqlite.org/2026/

HOMEPAGE= https://www.sqlite.org/
COMMENT= SQL database engine, shared C library and command line tool
LICENSE= public-domain

USE_LANGUAGES= c
GCC_REQD+= 16.2
USE_TOOLS+= gmake
HAS_CONFIGURE= yes
CONFIGURE_ENV+= CCACHE=none
CONFIGURE_ARGS+= --prefix=${PREFIX} --mandir=${PREFIX}/${PKGMANDIR}
.include "features.mk"
CONFIGURE_ARGS+= ${SQLITE_CONFIGURE_ARGS}
CPPFLAGS+= ${SQLITE_CPPFLAGS}
CFLAGS+= -std=gnu17
LDFLAGS+= ${COMPILER_RPATH_FLAG}${PREFIX}/lib
MAKE_FLAGS+= LDFLAGS=${LDFLAGS:Q}
PKGCONFIG_OVERRIDE+= sqlite3.pc.in

post-install:
	${SH} ${FILESDIR}/install-licenses.sh ${WRKSRC} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../mk/pthread.buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
