.include "../../devel/bmm150-sensorapi/Makefile.common"

DISTNAME= BMM150_SensorAPI-${BMM150_SENSORAPI_REVISION}
PKGNAME= bmm150-sensorapi-source-${BMM150_SENSORAPI_VERSION}
PKGREVISION= 1
CATEGORIES= devel
DISTFILES= ${BMM150_SENSORAPI_REVISION}.tar.gz
SITES.${DISTFILES}= -https://github.com/boschsensortec/BMM150_SensorAPI/archive/${BMM150_SENSORAPI_REVISION}.tar.gz
HOMEPAGE= https://github.com/boschsensortec/BMM150_SensorAPI
COMMENT= Patched Bosch BMM150 SensorAPI sources for base consumers
LICENSE= modified-bsd

WRKSRC= ${WRKDIR}/BMM150_SensorAPI-${BMM150_SENSORAPI_REVISION}
PATCHDIR= ${.CURDIR}/patches
NO_ARCH= yes
NO_CONFIGURE= yes
NO_BUILD= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tr
INSTALLATION_DIRS= share/bmm150-sensorapi

# The pinned GitHub archive stores these C sources with CRLF endings. Normalize
# only the patched C files so zero-fuzz pkgsrc patches are portable.
post-extract:
	${TR} -d '\015' < ${WRKSRC}/bmm150.c > ${WRKSRC}/bmm150.c.lf
	${MV} ${WRKSRC}/bmm150.c.lf ${WRKSRC}/bmm150.c
	${TR} -d '\015' < ${WRKSRC}/bmm150_defs.h > ${WRKSRC}/bmm150_defs.h.lf
	${MV} ${WRKSRC}/bmm150_defs.h.lf ${WRKSRC}/bmm150_defs.h

do-install:
	${INSTALL_DATA} ${WRKSRC}/bmm150.c ${WRKSRC}/bmm150.h \
	    ${WRKSRC}/bmm150_defs.h ${WRKSRC}/LICENSE \
	    ${DESTDIR}${PREFIX}/share/bmm150-sensorapi/
	${INSTALL_DATA} ${.CURDIR}/README.md \
	    ${DESTDIR}${PREFIX}/share/bmm150-sensorapi/README.EmberBSD.md

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/bmm150-sensorapi \( -type f -o -type l \) -print | ${SORT};
CHECK_INTERPRETER_SKIP+= share/bmm150-sensorapi/*
.include "../../mk/bsd.pkg.mk"
