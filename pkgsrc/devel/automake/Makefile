# $NetBSD: Makefile,v 1.122 2026/06/22 19:09:42 wiz Exp $
# Origin: pkgsrc devel/automake; EmberBSD current release update.

DISTNAME=	automake-1.19
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GNU:=automake/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.gnu.org/software/automake/automake.html
COMMENT=	GNU Standards-compliant Makefile generator
LICENSE=	gnu-gpl-v2

AUTOCONF_REQD+=	2.73

.include "../../mk/bsd.prefs.mk"

# Origin: EmberBSD (AI-assisted). aclocal and automake neither run m4 nor
# record its path; GNU m4 is a runtime dependency for the autoconf they
# drive. pkgsrc refuses the build-host m4 as a target runtime tool, so a
# cross build depends on the target m4 package instead.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
USE_TOOLS+=	autoconf gm4 perl:run
DEPENDS+=	m4>=1.4:../../devel/m4
# Configure substitutes its own shell, the build-host CONFIG_SHELL, for
# @SHELL@ in the DJGPP-only SHELL assignment of automake. The
# target runs /bin/sh, as a native build records.
SUBST_CLASSES+=		target-sh
SUBST_STAGE.target-sh=	post-build
SUBST_MESSAGE.target-sh=	Recording the target shell in automake.
SUBST_FILES.target-sh=	bin/automake
SUBST_SED.target-sh=	-e "s|'${CONFIG_SHELL}'|'/bin/sh'|"
.else
USE_TOOLS+=	autoconf gm4:run perl:run
.endif

PLIST_SUBST+=		PKG_DIR_VERSION=1.19
GNU_CONFIGURE=		yes
INFO_FILES=		yes
TEST_TARGET=		check

.include "../../mk/bsd.pkg.mk"
