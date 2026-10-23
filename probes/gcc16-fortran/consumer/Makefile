# SPDX-License-Identifier: BSD-2-Clause
DISTNAME= emberbsd-fortran-consumer-1.0
CATEGORIES= devel
MASTER_SITES= # none
DISTFILES= # none
COMMENT= GCC16 Fortran runtime and Libtool consumer probe
LICENSE= 2-clause-bsd
USE_LANGUAGES= c fortran
USE_LIBTOOL= yes
NO_CONFIGURE= yes
BUILD_TARGET= all
INSTALLATION_DIRS= bin lib
WRKSRC= ${WRKDIR}/consumer

post-extract:
	${RUN}${MKDIR} ${WRKSRC}
	${CP} ${FILESDIR}/consumer.f90 ${FILESDIR}/f77.f ${FILESDIR}/main.c ${WRKSRC}

do-build:
	${RUN}cd ${WRKSRC} && ${LIBTOOL} --tag=FC --mode=compile ${FC} ${FCFLAGS} -c consumer.f90 -o consumer.lo
	${RUN}cd ${WRKSRC} && ${LIBTOOL} --tag=F77 --mode=compile ${FC} ${FFLAGS} -c f77.f -o f77.lo
	${RUN}cd ${WRKSRC} && ${LIBTOOL} --tag=FC --mode=link ${FC} ${LDFLAGS} -o libemberfortran.la consumer.lo f77.lo -rpath ${PREFIX}/lib -version-info 1:0:0
	${RUN}cd ${WRKSRC} && ${CC} ${CFLAGS} -c main.c -o main.o
	${RUN}cd ${WRKSRC} && ${LIBTOOL} --tag=FC --mode=link ${FC} ${LDFLAGS} -o ember-fortran-consumer main.o libemberfortran.la

do-install:
	${LIBTOOL} --mode=install ${INSTALL_LIB} ${WRKSRC}/libemberfortran.la ${DESTDIR}${PREFIX}/lib/libemberfortran.la
	${LIBTOOL} --mode=install ${INSTALL_PROGRAM} ${WRKSRC}/ember-fortran-consumer ${DESTDIR}${PREFIX}/bin/ember-fortran-consumer

.include "../../lang/gcc16-fortran-devel/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
