# $NetBSD$
# Library sources are the complete upstream post-release state at a06f1ad.
DISTNAME= sha1collisiondetection-1.0.3
PKGREVISION= 2
CATEGORIES= devel security
MASTER_SITES= ${MASTER_SITE_GITHUB:=cr-marcstevens/}
GITHUB_TAG= stable-v${PKGVERSION_NOREV}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/cr-marcstevens/sha1collisiondetection/
COMMENT= SHA-1 implementation with cryptanalytic collision detection
LICENSE= mit

WRKSRC= ${WRKDIR}/sha1collisiondetection-${GITHUB_TAG}
USE_LIBTOOL= yes
NO_CONFIGURE= yes
INSTALLATION_DIRS= bin include/sha1dc lib lib/pkgconfig

do-build:
	cd ${WRKSRC} && ${LIBTOOL} --tag=CC --mode=compile ${CC} ${CPPFLAGS} ${CFLAGS} -c lib/sha1.c -o sha1.lo
	cd ${WRKSRC} && ${LIBTOOL} --tag=CC --mode=compile ${CC} ${CPPFLAGS} ${CFLAGS} -c lib/ubc_check.c -o ubc_check.lo
	cd ${WRKSRC} && ${LIBTOOL} --tag=CC --mode=link ${CC} ${CFLAGS} ${LDFLAGS} -o libsha1detectcoll.la sha1.lo ubc_check.lo -rpath ${PREFIX}/lib -version-info 1:0:0
	cd ${WRKSRC} && ${LIBTOOL} --tag=CC --mode=compile ${CC} ${CPPFLAGS} ${CFLAGS} -Ilib -c src/main.c -o main.lo
	cd ${WRKSRC} && ${LIBTOOL} --tag=CC --mode=link ${CC} ${CFLAGS} ${LDFLAGS} -o sha1dcsum main.lo libsha1detectcoll.la

do-install:
	${LIBTOOL} --mode=install ${INSTALL_LIB} ${WRKSRC}/libsha1detectcoll.la ${DESTDIR}${PREFIX}/lib
	${LIBTOOL} --mode=install ${INSTALL_PROGRAM} ${WRKSRC}/sha1dcsum ${DESTDIR}${PREFIX}/bin/sha1dcsum
	${LN} -s sha1dcsum ${DESTDIR}${PREFIX}/bin/sha1dcsum_partialcoll
	${INSTALL_DATA} ${WRKSRC}/lib/sha1.h ${DESTDIR}${PREFIX}/include/sha1dc/sha1.h
	${SED} -e 's|@PREFIX@|${PREFIX}|g' -e 's|@VERSION@|${PKGVERSION_NOREV}|g' ${FILESDIR}/sha1detectcoll.pc.in > ${DESTDIR}${PREFIX}/lib/pkgconfig/sha1detectcoll.pc

.include "../../mk/bsd.pkg.mk"
