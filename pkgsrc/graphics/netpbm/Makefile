# $NetBSD: Makefile,v 1.261 2026/06/14 19:01:56 nia Exp $

DISTNAME=	netpbm-11.02.31
CATEGORIES=	graphics
# Public SVN mirror: stable@5432, released 2026-10-25. Not an upstream tarball.
MASTER_SITES=	${MASTER_SITE_GITHUB:=jwilk-mirrors/}
GITHUB_PROJECT=	netpbm
GITHUB_TAG=	125b3245dabc345d5327cbb62e275a268b139388
DISTFILES=	${DISTNAME}-${GITHUB_TAG}${EXTRACT_SUFX} netpbm-docs-r4908${EXTRACT_SUFX}
SITES.netpbm-docs-r4908.tar.gz=	${MASTER_SITE_LOCAL}
# Retain the existing pkgsrc-generated manual-page archive.

MAINTAINER=	adam@NetBSD.org
HOMEPAGE=	https://netpbm.sourceforge.net/
COMMENT=	Toolkit for conversion of images between different formats
LICENSE=	gnu-gpl-v2

.include "../../mk/bsd.prefs.mk"

USE_TOOLS+=	gmake gdate flex pax perl
USE_FEATURES=	snprintf

INSTALL_TARGET=	install-dev install-run
MAKE_ENV+=	INSTALL=${INSTALL:Q} STRIPFLAG=${_STRIPFLAG_INSTALL:Q} \
		pkgdir=${STAGEDIR} MACHINE=${MACHINE:Q}
MAKE_FLAGS+=	PKGMANDIR=${PKGMANDIR}
PLIST_VARS+=	manweb
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The optional Perl browser helper cannot run in a minimal cross sysroot.
# SCRIPTS on the make command line would also empty the script lists of
# every subdirectory, so drop manweb from the top-level list only.
SUBST_CLASSES+=		manweb
SUBST_STAGE.manweb=	pre-configure
SUBST_MESSAGE.manweb=	Omitting manweb from the cross build.
SUBST_FILES.manweb=	GNUmakefile
SUBST_SED.manweb=	-e 's/^SCRIPTS = manweb$$/SCRIPTS =/'
.else
PLIST.manweb=	yes
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Netpbm executes these compiler-built generators during its cross build,
# so they take the build machine compiler and flags, never the target ones.
MAKE_FLAGS+=	CC_FOR_BUILD=${NATIVE_CC:Q}
MAKE_FLAGS+=	LD_FOR_BUILD=${NATIVE_CC:Q}
MAKE_FLAGS+=	CFLAGS_FOR_BUILD=${NATIVE_CPPFLAGS:Q}\ ${NATIVE_CFLAGS:Q}
MAKE_FLAGS+=	LDFLAGS_FOR_BUILD=${NATIVE_LDFLAGS:Q}
.else
MAKE_FLAGS+=	CFLAGS_FOR_BUILD=${CFLAGS:Q}
MAKE_FLAGS+=	LDFLAGS_FOR_BUILD=${LDFLAGS:Q}
.endif
MAKE_FILE=	GNUmakefile
REPLACE_PERL+=	converter/pbm/pbmtox10bm
REPLACE_PERL+=	editor/pnmflip
REPLACE_PERL+=	editor/pnmquant
REPLACE_PERL+=	editor/ppmfade
REPLACE_PERL+=	editor/ppmquant
REPLACE_PERL+=	editor/ppmshadow
REPLACE_PERL+=	generator/ppmrainbow
REPLACE_PERL+=	manweb
REPLACE_SH+=	buildtools/stamp-date
STAGEDIR=	${WRKDIR}/staging
WRKSRC=		${WRKDIR}/netpbm-${GITHUB_TAG}

WRAPPER_REORDER_CMDS+=	reorder:l:rle:netpbm

SUBST_CLASSES+=		rgb_txt
SUBST_STAGE.rgb_txt=	pre-configure
SUBST_MESSAGE.rgb_txt=	Configure RGB_TXT
SUBST_FILES.rgb_txt=	config.mk
SUBST_SED.rgb_txt+=	-e 's,/usr/share/netpbm/rgb.txt,${PREFIX}/share/netpbm/rgb.txt,'

# needs pkg-config and x11?!
TEST_TARGET=	test


# only used if NEED_RUNTIME_PATH is set, so set it unconditionally
MAKE_FLAGS+=	NETPBMLIB_RUNTIME_PATH=${PREFIX}

MAKE_FLAGS.NetBSD+=	NEED_RUNTIME_PATH=Y
MAKE_FLAGS.Darwin+=	NETPBMLIBTYPE=dylib
MAKE_FLAGS.Darwin+=	NETPBMLIBSUFFIX=dylib
MAKE_FLAGS.SunOS+=	LDSHLIB=-shared
MAKE_FLAGS.SunOS+=	NEED_RUNTIME_PATH=Y
MAKE_FLAGS.SunOS+=	NETWORKLD="-lsocket -lnsl"

# Uses "old-style function definitions" in getopt.c.
FORCE_C_STD=		gnu89

# Fix implicit function declarations.
CFLAGS.NetBSD+=		-D_NETBSD_SOURCE
CFLAGS.SunOS+=		-D__EXTENSIONS__

.if ${OS_VARIANT} == "SCOOSR5"
MAKE_FLAGS+=	NETWORKLD="-lsocket -lresolv"
.endif

# Ridiculous but they hardcode it in every file so we have no choice.
SUBST_CLASSES+=		xopen
SUBST_STAGE.xopen=	pre-configure
SUBST_FILES.xopen=	*/*.c */*/*.c */*/*/*.c */*/*/*/*.c */*/*/*/*/*.c
SUBST_FILES.xopen+=	lib/util/lexheader
SUBST_SED.xopen=	-e '/_XOPEN_SOURCE/s/500/600/'
SUBST_SED.xopen+=	-e '/_XOPEN_SOURCE/s/1$$/600/'
SUBST_SED.xopen+=	-e '/_XOPEN_SOURCE[^0-9]*\//s/SOURCE/SOURCE 600/'
SUBST_SED.xopen+=	-e '/_XOPEN_SOURCE$$/s/E$$/E 600/'
SUBST_SED.xopen+=	-e '/_POSIX_SOURCE.*fdopen/s/_POSIX_SOURCE/_XOPEN_SOURCE 600/'

INSTALLATION_DIRS=	${PKGMANDIR}/man1 ${PKGMANDIR}/man3 ${PKGMANDIR}/man5 share/netpbm

.include "options.mk"

post-extract:
	cd ${WRKSRC} && ${CP} config.mk.in config.mk
	${ECHO} "CFLAGS_SHLIB = -fPIC" >> ${WRKSRC}/config.mk
	${ECHO} "JPEGLIB = ${BUILDLINK_PREFIX.jpeg}/lib/libjpeg.so" >> ${WRKSRC}/config.mk
	${ECHO} "JPEGHDR_DIR = ${BUILDLINK_PREFIX.jpeg}/include" >> ${WRKSRC}/config.mk
	${ECHO} "TIFFLIB = ${BUILDLINK_PREFIX.tiff}/lib/libtiff.so" >> ${WRKSRC}/config.mk
	${ECHO} "TIFFHDR_DIR = ${BUILDLINK_PREFIX.tiff}/include" >> ${WRKSRC}/config.mk
.if !empty(PKG_OPTIONS:Mjasper)
	${ECHO} "JASPERLIB = ${BUILDLINK_PREFIX.jasper}/lib/libjasper.so" >> ${WRKSRC}/config.mk
	${ECHO} "JASPERHDR_DIR = ${BUILDLINK_PREFIX.jasper}/include" >> ${WRKSRC}/config.mk
.else
	${ECHO} "JASPERLIB = NONE" >> ${WRKSRC}/config.mk
.endif
	${ECHO} "ZLIB = ${BUILDLINK_PREFIX.zlib}/lib/libz.so" >> ${WRKSRC}/config.mk
	${ECHO} "ZHDR_DIR = ${BUILDLINK_PREFIX.zlib}/include" >> ${WRKSRC}/config.mk
.if ${OPSYS} == "Darwin"
	${ECHO} 'LDSHLIB=-dynamiclib -install_name $$(PREFIX)/lib/libnetpbm.$$(MAJ).dylib -compatibility_version $$(MAJ) -current_version $$(MAJ).$$(MIN)' >> ${WRKSRC}/config.mk
.endif

pre-install:
	${RM} -fr ${STAGEDIR}
	${MKDIR} -p ${STAGEDIR}/man/web

post-install:
	cd ${STAGEDIR} && 					\
	${RM} -rf ${PKGMANDIR}/web && 				\
	${RM} -rf man/web && 					\
	${MKDIR} share &&					\
	${MV} misc share/netpbm && 				\
	${CHOWN} -R ${BINOWN}:${BINGRP} . &&			\
	pax -rwppm . ${DESTDIR}${PREFIX}
	${RM} -fr ${STAGEDIR}
	${INSTALL_DATA} ${WRKDIR}/userguide/*.1 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1
	${INSTALL_DATA} ${WRKDIR}/userguide/*.3 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man3
	${INSTALL_DATA} ${WRKDIR}/userguide/*.5 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man5
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${RM} -f ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/manweb.1
.endif

# dladdr identifies libnetpbm itself; static/other hosts keep upstream defaults.
.if !empty(OPSYS:MDarwin) || !empty(OPSYS:MNetBSD) || !empty(OPSYS:MLinux)
.include "../../mk/dlopen.buildlink3.mk"
CPPFLAGS+=	-DNETPBM_HAVE_DLADDR ${DL_CFLAGS}
LDFLAGS+=	${DL_LDFLAGS} ${DL_LIBS} ${BUILDLINK_LDADD.dl}
.endif

.include "../../devel/zlib/buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../graphics/tiff/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../mk/jpeg.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
