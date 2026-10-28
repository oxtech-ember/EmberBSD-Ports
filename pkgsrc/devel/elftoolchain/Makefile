# $NetBSD: Makefile,v 1.18 2025/11/17 11:00:35 wiz Exp $

DISTNAME=	elftoolchain-0.7.1
PKGREVISION=	2
CATEGORIES=	devel
MASTER_SITES=	https://downloads.sourceforge.net/project/elftoolchain/Sources/elftoolchain-0.7.1/
EXTRACT_SUFX=	.tar.bz2

MAINTAINER=	agc@NetBSD.org
HOMEPAGE=	https://elftoolchain.sourceforge.net/
COMMENT=	Compilation tools (nm, ar, as, ld, etc.) for the ELF object format
LICENSE=	modified-bsd

CONFLICTS=	libelf-[0-9]*

NOT_FOR_PLATFORM=	Darwin-*-*

MAKE_JOBS_SAFE=	no

USE_BSD_MAKEFILE=	yes
USE_TOOLS+=		m4 lex
MAKE_ENV+=		${BSD_MAKE_ENV}
MAKE_FLAGS+=		MKPROFILE=yes
MAKE_FLAGS+=		INCSDIR=${PREFIX}/include
MAKE_FLAGS+=		CWARNFLAGS=${CWARNFLAGS:Q}

INSTALLATION_DIRS=	bin include include/sys lib
INSTALLATION_DIRS+=	${PKGMANDIR}/man1 ${PKGMANDIR}/cat1 ${PKGMANDIR}/html1
INSTALLATION_DIRS+=	${PKGMANDIR}/man3 ${PKGMANDIR}/cat3 ${PKGMANDIR}/html3
INSTALLATION_DIRS+=	${PKGMANDIR}/man5 ${PKGMANDIR}/cat5 ${PKGMANDIR}/html5

# The source receiver also serves the native base library. It must not
# install another implementation in an EmberBSD package prefix.
.include "../../mk/bsd.prefs.mk"
.if (${OPSYS} == "NetBSD" && (${EMBERBSD_PORTS:Uno:tl} == "yes" || \
    exists(${.PARSEDIR}/../../EMBERBSD-PKGSRC-REVISION))) || \
    exists(${TOOLS_CROSS_DESTDIR}/usr/share/emberbsd/ports/elftoolchain.distinfo)
PKG_FAIL_REASON+= "EmberBSD base provides libelf. Rebuild the base from this Ports source recipe instead of installing this package."
.endif

post-install:
	# Global INCSDIR selects the package include root for every subdirectory.
	# Keep both the wrapper and its generated sys header at distinct paths.
	${RUN} sysobj=`cd ${WRKSRC:Q}/common/sys && \
		${SETENV} ${MAKE_ENV} ${MAKE_PROGRAM} ${MAKE_FLAGS} -V .OBJDIR` && \
		${INSTALL_DATA} "$$sysobj/elfdefinitions.h" \
		    ${DESTDIR}${PREFIX}/include/sys/elfdefinitions.h
	${INSTALL_DATA} ${WRKSRC}/common/elfdefinitions.h \
	    ${DESTDIR}${PREFIX}/include/elfdefinitions.h

.include "../../mk/bsd.pkg.mk"
