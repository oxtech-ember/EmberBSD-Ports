# $NetBSD$
# Origin: Apple bootstrap_cmds; native Mach interface generator.

DISTNAME=	bootstrap_cmds-138
PKGNAME=	mig-138
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=apple-oss-distributions/}
GITHUB_PROJECT=	bootstrap_cmds
GITHUB_TAG=	bootstrap_cmds-138
WRKSRC=		${WRKDIR}/bootstrap_cmds-bootstrap_cmds-138

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/apple-oss-distributions/bootstrap_cmds
COMMENT=	Mach interface generator for native Darwin builds
LICENSE=	apple-public-source-license AND apple-public-source-license-1.0 AND cmu-mig-license

ONLY_FOR_PLATFORM=	Darwin-*-*
USE_LANGUAGES=		c
USE_TOOLS+=		bash:run bison flex gm4
REPLACE_BASH+=		migcom.tproj/mig.sh
INSTALLATION_DIRS=	bin libexec ${PKGMANDIR}/man1 share/doc/mig

MIG_SRC=	${WRKSRC}/migcom.tproj
MIG_SOURCES=	error.c global.c header.c mig.c routine.c server.c \
		statement.c string.c type.c user.c utils.c y.tab.c lexxer.c

do-build:
	cd ${MIG_SRC} && ${SETENV} M4=${TOOLS_PATH.gm4:Q} ${TOOLS_PATH.bison} -y -d parser.y
	cd ${MIG_SRC} && ${TOOLS_PATH.flex} -o lexxer.c lexxer.l
	cd ${MIG_SRC} && ${CC} ${CPPFLAGS} ${CFLAGS} -DMIG_VERSION='"bootstrap_cmds-138"' \
	    -I. ${MIG_SOURCES} ${LDFLAGS} -o migcom

do-install:
	${INSTALL_SCRIPT} ${MIG_SRC}/mig.sh ${DESTDIR}${PREFIX}/bin/mig
	${INSTALL_PROGRAM} ${MIG_SRC}/migcom ${DESTDIR}${PREFIX}/libexec/migcom
	${INSTALL_MAN} ${MIG_SRC}/mig.1 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/mig.1
	${INSTALL_MAN} ${MIG_SRC}/migcom.1 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/migcom.1
	${INSTALL_DATA} ${WRKSRC}/APPLE_LICENSE ${DESTDIR}${PREFIX}/share/doc/mig/APSL-2.0
	${INSTALL_DATA} ${FILESDIR}/apple-public-source-license-1.0 ${DESTDIR}${PREFIX}/share/doc/mig/APSL-1.0
	${INSTALL_DATA} ${FILESDIR}/cmu-mig-license ${DESTDIR}${PREFIX}/share/doc/mig/CMU

.include "../../mk/bsd.pkg.mk"
