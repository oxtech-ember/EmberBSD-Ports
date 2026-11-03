.include "../../devel/bmi270-sensorapi/Makefile.common"

DISTNAME= BMI270_SensorAPI-${BMI270_SENSORAPI_REVISION}
PKGNAME= bmi270-sensorapi-source-${BMI270_SENSORAPI_VERSION}
PKGREVISION= 2
CATEGORIES= devel
DISTFILES= ${BMI270_SENSORAPI_REVISION}.tar.gz
SITES.${DISTFILES}= -https://github.com/boschsensortec/BMI270_SensorAPI/archive/${BMI270_SENSORAPI_REVISION}.tar.gz
HOMEPAGE= https://github.com/boschsensortec/BMI270_SensorAPI
COMMENT= Patched Bosch BMI270 base SensorAPI sources for OS consumers
LICENSE= modified-bsd

WRKSRC= ${WRKDIR}/BMI270_SensorAPI-${BMI270_SENSORAPI_REVISION}
PATCHDIR= ${.CURDIR}/patches
NO_ARCH= yes
NO_CONFIGURE= yes
NO_BUILD= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tr
INSTALLATION_DIRS= share/bmi270-sensorapi

# Normalize the patched upstream files from the pinned GitHub archive for
# zero-fuzz patching across the selected native package toolchain.
post-extract:
	${TR} -d '\015' < ${WRKSRC}/bmi2.c > ${WRKSRC}/bmi2.c.lf
	${MV} ${WRKSRC}/bmi2.c.lf ${WRKSRC}/bmi2.c
	${TR} -d '\015' < ${WRKSRC}/bmi2_defs.h > ${WRKSRC}/bmi2_defs.h.lf
	${MV} ${WRKSRC}/bmi2_defs.h.lf ${WRKSRC}/bmi2_defs.h

do-install:
	${INSTALL_DATA} ${WRKSRC}/bmi2.c ${WRKSRC}/bmi2.h \
	    ${WRKSRC}/bmi2_defs.h ${WRKSRC}/bmi270.c ${WRKSRC}/bmi270.h \
	    ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/bmi270-sensorapi/
	${INSTALL_DATA} ${.CURDIR}/README.md \
	    ${DESTDIR}${PREFIX}/share/bmi270-sensorapi/README.EmberBSD.md

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/bmi270-sensorapi \( -type f -o -type l \) -print | ${SORT};
CHECK_INTERPRETER_SKIP+= share/bmi270-sensorapi/*
.include "../../mk/bsd.pkg.mk"
