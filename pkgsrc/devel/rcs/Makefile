# Origin: pkgsrc devel/rcs; EmberBSD update (AI-assisted).

DISTNAME=		rcs-5.10.1
CATEGORIES=		devel scm
MASTER_SITES=		${MASTER_SITE_GNU:=rcs/}
EXTRACT_SUFX=		.tar.lz

MAINTAINER=		pkgsrc-users@NetBSD.org
HOMEPAGE=		https://www.gnu.org/software/rcs/
COMMENT=		GNU Revision Control System - version control software
LICENSE=		gnu-gpl-v3

BUILD_DEFS+=		RCS_LOCALID RCS_RLOG_EXPLICIT_COMMITID

.if ${RCS_RLOG_EXPLICIT_COMMITID:Uno} == "yes"
CPPFLAGS+=		-DRCS_RLOG_EXPLICIT_COMMITID
.endif

.if defined(RCS_LOCALID)
CPPFLAGS+=		-DLOCALID=\"${RCS_LOCALID}\"
.endif

GNU_CONFIGURE=		yes
TEST_TARGET=		check
# The release includes generated manuals; patches update both source and output.
USE_TOOLS+=		gmake tee diff diff3

DEPENDS+=		ed-[0-9]*:../../editors/ed
DEPENDS+=		diffutils>=3.12:../../devel/diffutils
CONFIGURE_ENV+=		ac_cv_path_ED=${PREFIX:Q}/bin/ged

.include "../../mk/bsd.prefs.mk"

# the native diff/diff3 is not sufficient for rcs
.if ${OPSYS} == "SunOS" || ${OPSYS} == "OSF1" || ${OPSYS} == "AIX" || ${OPSYS} == "Minix"
TOOLS_PLATFORM.diff=
TOOLS_PLATFORM.diff3=
.endif
# DIFF is already in CONFIGURE_ENV
CONFIGURE_ENV+=		DIFF3=${TOOLS_PATH.diff3}

REPLACE_SH=		build-aux/extract-help
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
REPLACE_SH+=		src/sub.TEMPLATE src/rcsfreeze.sh
.endif

INFO_FILES=	yes

# configure will be modified by pkgsrc framework with timestamp update.
# sync timestamp with man/REL to avoid regeneration of man.
post-configure:
	${TOUCH} -r ${WRKSRC}/man/REL ${WRKSRC}/configure

post-install:
	${INSTALL_SCRIPT} ${WRKSRC}/src/rcsfreeze ${DESTDIR}${PREFIX}/bin/rcsfreeze
	${INSTALL_MAN} ${WRKSRC}/man/rcsfreeze.1 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/rcsfreeze.1
	${LN} -s rlog ${DESTDIR}${PREFIX}/bin/rcslog
	${LN} -s rlog.1 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/rcslog.1

.include "../../mk/bsd.pkg.mk"

# Configure must record target runtime commands, not native build tools.
# diffutils is an explicit runtime dependency and supplies these interfaces.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CONFIGURE_ENV+= DIFF=${PREFIX:Q}/bin/gdiff DIFF3=${PREFIX:Q}/bin/gdiff3
CONFIGURE_ENV+= ac_cv_path_DIFF=${PREFIX:Q}/bin/gdiff
CONFIGURE_ENV+= ac_cv_path_DIFF3=${PREFIX:Q}/bin/gdiff3 rcs_cv_sane_diff3=yes
.endif
