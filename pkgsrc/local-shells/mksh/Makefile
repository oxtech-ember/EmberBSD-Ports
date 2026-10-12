# MirBSD Korn Shell at the current upstream R59c release.
# The pinned quarterly pkgsrc still carries R59b with a locally maintained
# source copy; this recipe tracks the upstream distribution tarball instead.
DISTNAME=	mksh-R59c
PKGNAME=	mksh-59c
CATEGORIES=	shells
MASTER_SITES=	https://www.mirbsd.org/MirOS/dist/mir/mksh/

HOMEPAGE=	http://mirbsd.de/mksh
COMMENT=	MirBSD Korn Shell
LICENSE=	miros

WRKSRC=		${WRKDIR}/mksh
PKG_SHELL=	bin/mksh

MAKE_ENV+=	USE_PRINTF_BUILTIN=1

INSTALLATION_DIRS=	bin ${PKGMANDIR}/man1 share/examples/mksh

# For check-portability's double brackets check.
CHECK_PORTABILITY_SKIP+=	Build.sh

do-build:
	cd ${WRKSRC} && ${SETENV} ${MAKE_ENV} LIBS=${LIBS:Q} \
	    ${TOOLS_SHELL} ${WRKSRC}/Build.sh -r

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/mksh ${DESTDIR}${PREFIX}/bin/mksh
	${INSTALL_MAN} ${WRKSRC}/mksh.1 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/
	${INSTALL_DATA} ${WRKSRC}/dot.mkshrc ${DESTDIR}${PREFIX}/share/examples/mksh/

# The upstream regression suite (test.sh, check.t) needs a Perl interpreter.
# Keep it out of the package build until the shell profile carries Perl.
# USE_TOOLS+=	perl
#do-test:
#	cd ${WRKSRC} && ${TOOLS_SHELL} ./test.sh -v

.include "../../mk/bsd.pkg.mk"
