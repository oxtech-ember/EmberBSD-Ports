# MirBSD Korn Shell at the current upstream R59c release.
# The pkgsrc bootstrap builds this package and copies files/ to make its
# first shell, so the recipe keeps a source copy, as pinned pkgsrc does.
# files/ holds the text files of the original mksh-R59c.tgz (SHA256
# 77ae1665a337f1c48c61d6b961db3e52119b38e58884d1c89684af31f87bc506).
# The binary OS/2 icon mksh.ico is not copied; no build uses it.
# profiles/shells/mksh-source.sh compares files/ with the archive.
DISTNAME=	mksh-R59c
PKGNAME=	mksh-59c
PKGREVISION=	2
CATEGORIES=	shells
MASTER_SITES=	# maintained locally
DISTFILES=	# empty

HOMEPAGE=	http://mirbsd.de/mksh
COMMENT=	MirBSD Korn Shell
LICENSE=	miros

POLICY_UPDATE_LIMITED=	bootstrap
BOOTSTRAP_PKG=		yes

WRKSRC=		${WRKDIR}/mksh
USE_TOOLS+=	perl:test
PERL5_REQD+=	5.44.0
TEST_DEPENDS+=	ed>=1.22.6:../../editors/ed
GCC_REQD+=	16.2

# The upstream archive does not contain pkgsrc's separate printf.c copy.
# Keep the supported upstream shell; printf comes from the base utilities.

INSTALLATION_DIRS=	bin ${PKGMANDIR}/man1 share/examples/mksh

.include "../../mk/bsd.prefs.mk"

# The bootstrap shell must not register itself as a login shell: its
# +INSTALL script would need that same shell. This matches both bootstrap
# prefixes, as in pinned pkgsrc.
.if ${TOOLS_PLATFORM.sh:N?*/bin/mksh}
PKG_SHELL=	bin/mksh
.endif

# For check-portability's double brackets check.
CHECK_PORTABILITY_SKIP+=	Build.sh

do-extract:
	${CP} -R ${FILESDIR} ${WRKSRC}

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
