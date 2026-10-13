# MirBSD Korn Shell at the current upstream R59c release.
# The pinned quarterly pkgsrc still carries R59b with a locally maintained
# source copy; this recipe tracks the upstream distribution tarball instead.
DISTNAME=	mksh-R59c
PKGNAME=	mksh-59c
PKGREVISION=	1
CATEGORIES=	shells
MASTER_SITES=	https://www.mirbsd.org/MirOS/dist/mir/mksh/
MASTER_SITES+=	https://mbsd.evolvis.org/MirOS/dist/mir/mksh/
EXTRACT_SUFX=	.tgz

HOMEPAGE=	http://mirbsd.de/mksh
COMMENT=	MirBSD Korn Shell
LICENSE=	miros

WRKSRC=		${WRKDIR}/mksh
PKG_SHELL=	bin/mksh
USE_TOOLS+=	perl:test
PERL5_REQD+=	5.44.0
TEST_DEPENDS+=	ed>=1.22.6:../../editors/ed
GCC_REQD+=	16.2

# The upstream archive does not contain pkgsrc's separate printf.c copy.
# Keep the supported upstream shell; printf comes from the base utilities.

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

# Build.sh generates a test driver that requires mksh syntax.
# Run this target from a controlling terminal to include job-control tests.
# GNU ed prints byte counts on stdout. Select upstream's matching cases.
# The harness requires -e to preserve FCEDIT in its minimal environment.
do-test:
	cd ${WRKSRC} && ${SETENV} PERL=${TOOLS_PERL5:Q} \
	    FCEDIT=${PREFIX:Q}/bin/ged ./mksh ./test.sh -v \
	    -e FCEDIT -C stdout-ed,no-stderr-ed

.include "../../mk/bsd.pkg.mk"
