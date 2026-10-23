# $NetBSD: Makefile,v 1.1 2026/04/13 15:36:31 kikadf Exp $

DISTNAME=	libevdev-chunk-20231112
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	-https://code.tetaneutral.net/mherrb/libevdev-openbsd/archive/20231112.tar.gz
DISTFILES=	${DISTNAME:S/chunk/openbsd/}${EXTRACT_SUFX}

MAINTAINER=	kikadf.01@gmail.com
HOMEPAGE=	https://code.tetaneutral.net/mherrb/libevdev-openbsd/
COMMENT=	Minimal set of libevdev functions
LICENSE=	mit

# The latest stable tag and upstream HEAD both resolve to this commit.
# Verified on 2026-10-19: d41a0fc04be7841b06a7cf172375dcbd91fdf3f5.
WRKSRC=		${WRKDIR}/libevdev-openbsd

PKGCONFIG_OVERRIDE+=	libevdev.pc.in

SUBST_CLASSES+=		prefix
SUBST_STAGE.prefix=	pre-configure
SUBST_FILES.prefix=	Makefile
SUBST_SED.prefix=	-e 's,/usr/local,${PREFIX},g'

INSTALLATION_DIRS+=	lib/pkgconfig
INSTALLATION_DIRS+=	include/libevdev

do-install:
	${INSTALL_LIB} ${WRKSRC}/libevdev.so ${DESTDIR}${PREFIX}/lib
	${INSTALL_LIB} ${WRKSRC}/libevdev.so.0 ${DESTDIR}${PREFIX}/lib
	${INSTALL_LIB} ${WRKSRC}/libevdev.so.0.0 ${DESTDIR}${PREFIX}/lib
	${INSTALL_DATA} ${WRKSRC}/libevdev.a ${DESTDIR}${PREFIX}/lib
	${INSTALL_DATA} ${WRKSRC}/libevdev/libevdev.h ${DESTDIR}${PREFIX}/include/libevdev
	${INSTALL_DATA} ${WRKSRC}/libevdev.pc ${DESTDIR}${PREFIX}/lib/pkgconfig

# Origin: EmberBSD (AI-assisted). The upstream BSD make framework uses
# build-host linker syntax. Cross builds select the target tools explicitly.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
do-build:
	cd ${WRKSRC} && ${CC} ${CPPFLAGS} ${CFLAGS} -fPIC -I. -c libevdev.c -o libevdev.o
	cd ${WRKSRC} && ${AR} cr libevdev.a libevdev.o && ${RANLIB} libevdev.a
	cd ${WRKSRC} && ${CC} ${LDFLAGS} -shared -Wl,-soname,libevdev.so.0 -o libevdev.so.0.0 libevdev.o
	cd ${WRKSRC} && ${LN} -sf libevdev.so.0.0 libevdev.so.0 && ${LN} -sf libevdev.so.0.0 libevdev.so
	${SED} -e 's,@prefix@,${PREFIX},g' -e 's,@exec_prefix@,$${prefix},g' \
	    -e 's,@libdir@,$${exec_prefix}/lib,g' -e 's,@includedir@,$${prefix}/include,g' \
	    -e 's,@PACKAGE_VERSION@,1.13.1,g' ${WRKSRC}/libevdev.pc.in > ${WRKSRC}/libevdev.pc
.endif

.include "../../devel/input-headers/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
