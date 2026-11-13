# Native PaX ELF note tool from the shared EmberBSD OS source.
DISTNAME= emberbsd-paxctl-20261113
CATEGORIES= sysutils
MASTER_SITES= # individual immutable OS source files below
DISTFILES= emberbsd-paxctl-20261113.c emberbsd-exec-elf-20261113.h \
           emberbsd-aarch64-elf-20261113.h emberbsd-amd64-elf-20261113.h
EXTRACT_ONLY= # individual source files
OS_REV= 5f7ef1ccf8af4e477e065147438597b2a10ada81
OS_RAW= https://raw.githubusercontent.com/oxtech-ember/EmberBSD/${OS_REV}
SITES.emberbsd-paxctl-20261113.c= -${OS_RAW}/usr.sbin/paxctl/paxctl.c
SITES.emberbsd-exec-elf-20261113.h= -${OS_RAW}/sys/sys/exec_elf.h
SITES.emberbsd-aarch64-elf-20261113.h= -${OS_RAW}/sys/arch/aarch64/include/elf_machdep.h
SITES.emberbsd-amd64-elf-20261113.h= -${OS_RAW}/sys/arch/amd64/include/elf_machdep.h

MAINTAINER= oxtech-ember@users.noreply.github.com
HOMEPAGE= https://github.com/oxtech-ember/EmberBSD
COMMENT= Native host tool for EmberBSD ELF PaX notes
LICENSE= modified-bsd
USE_LANGUAGES= c
USE_CROSS_COMPILE?= no

.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:tl} == "yes"
PKG_SKIP_REASON= "emberbsd-paxctl is a native host tool"
.endif

.if ${MACHINE_ARCH} == "aarch64"
_PAX_HOST_ARCH= aarch64
.elif ${MACHINE_ARCH} == "x86_64"
_PAX_HOST_ARCH= amd64
.else
PKG_SKIP_REASON= "emberbsd-paxctl needs an OS host ELF header for ${MACHINE_ARCH}"
.endif

INSTALLATION_DIRS= bin share/doc/emberbsd-paxctl

do-extract:
	${RUN}${MKDIR} ${WRKDIR}/usr.sbin/paxctl ${WRKDIR}/sys/sys ${WRKDIR}/nbinclude/machine
	${RUN}${CP} ${DISTDIR}/emberbsd-paxctl-20261113.c ${WRKDIR}/usr.sbin/paxctl/paxctl.c
	${RUN}${CP} ${DISTDIR}/emberbsd-exec-elf-20261113.h ${WRKDIR}/sys/sys/exec_elf.h
	${RUN}${CP} ${DISTDIR}/emberbsd-${_PAX_HOST_ARCH}-elf-20261113.h ${WRKDIR}/nbinclude/machine/elf_machdep.h
	${RUN}${PRINTF} '#include <nbcompat.h>\n' > ${WRKDIR}/nbtool_config.h

do-build:
	${RUN}${CC} ${CPPFLAGS} ${CFLAGS} -I${WRKDIR} -DHAVE_NBTOOL_CONFIG_H=1 \
	    ${WRKDIR}/usr.sbin/paxctl/paxctl.c ${LDFLAGS} -lnbcompat -o ${WRKDIR}/paxctl

do-install:
	${RUN}for source in ${DISTDIR}/emberbsd-paxctl-20261113.c ${DISTDIR}/emberbsd-exec-elf-20261113.h ${DISTDIR}/emberbsd-aarch64-elf-20261113.h; do \
	    ${AWK} '/^\/\*-/ { copying=1 } copying { print } copying && /\*\// { exit }' "$$source"; \
	    ${ECHO}; done > ${WRKDIR}/COPYRIGHT
	${INSTALL_DATA} ${WRKDIR}/COPYRIGHT ${DESTDIR}${PREFIX}/share/doc/emberbsd-paxctl/COPYRIGHT
	${INSTALL_PROGRAM} ${WRKDIR}/paxctl ${DESTDIR}${PREFIX}/bin/paxctl

.include "../../pkgtools/libnbcompat/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
