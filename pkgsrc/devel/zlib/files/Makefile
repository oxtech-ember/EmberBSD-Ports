# $NetBSD: Makefile,v 1.4 2012/09/02 14:56:17 wiz Exp $
#
# Replacement Makefile for zlib.

OBJS=	adler32.o compress.o crc32.o deflate.o gzclose.o gzlib.o gzread.o \
	gzwrite.o infback.o inffast.o inflate.o inftrees.o trees.o \
	uncompr.o zutil.o
LOBJS=	${OBJS:R:S/$/.lo/g}

all: libz.la

# Headers are real inputs for both ordinary and libtool objects.
${OBJS} ${LOBJS}: zlib.h zconf.h
adler32.o crc32.o deflate.o infback.o inffast.o inflate.o inftrees.o trees.o zutil.o \
    adler32.lo crc32.lo deflate.lo infback.lo inffast.lo inflate.lo inftrees.lo trees.lo zutil.lo: zutil.h
crc32.o crc32.lo: crc32.h
deflate.o deflate.lo trees.o trees.lo: deflate.h
trees.o trees.lo: trees.h
gzclose.o gzclose.lo gzlib.o gzlib.lo gzread.o gzread.lo gzwrite.o gzwrite.lo zutil.o zutil.lo: gzguts.h
infback.o infback.lo inffast.o inffast.lo inflate.o inflate.lo inftrees.o inftrees.lo: inftrees.h inflate.h
infback.o infback.lo inffast.o inffast.lo inflate.o inflate.lo: inffast.h
inftrees.o inftrees.lo: inffixed.h

libz.la: ${LOBJS}
	${LIBTOOL} --mode=link --tag=CC ${CC} ${LDFLAGS} ${CFLAGS} -o ${.TARGET} \
	    ${LOBJS} -version-info 1:2 -rpath ${PREFIX}/lib

libz.a: ${OBJS}
	${AR} cq ${.TARGET} ${OBJS}
	${RANLIB} ${.TARGET}

.SUFFIXES: .c .o .lo

.c.o:
	${CC} -c ${CFLAGS} -o ${.TARGET} ${.IMPSRC}

.c.lo:
	${LIBTOOL} --mode=compile --tag=CC ${CC} -c ${CFLAGS} -o ${.TARGET} ${.IMPSRC}
