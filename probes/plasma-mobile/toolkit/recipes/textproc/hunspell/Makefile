# $NetBSD: Makefile,v 1.46 2026/05/07 16:34:35 adam Exp $

DISTNAME=	hunspell-1.7.5
PKGREVISION=	1
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=hunspell/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://hunspell.github.io/
COMMENT=	Improved spellchecker
LICENSE=	mpl-1.1 OR gnu-lgpl-v2.1 OR gnu-gpl-v2

USE_CXX_FEATURES=	c++11
USE_LIBTOOL=		yes
USE_TOOLS+=		pkg-config autoreconf autoconf automake autopoint
USE_PKGLOCALEDIR=	yes
USE_LANGUAGES=		c c++
GNU_CONFIGURE=		yes
CONFIGURE_ARGS+=	--with-ui
PKGCONFIG_OVERRIDE+=	hunspell.pc.in

GCC_REQD+=		7
FAKE_NCURSES=		yes

CPPFLAGS.SunOS+=	-D_XPG6

SUBST_CLASSES+=		paths
SUBST_MESSAGE.paths=	Fixing default path to dictionaries.
SUBST_STAGE.paths=	pre-configure
SUBST_FILES.paths=	man/hunspell.1 man/hu/hunspell.1 src/tools/hunspell.cxx
SUBST_SED.paths+=	-e 's,/usr/share/hunspell,${PREFIX}/share/hunspell,g'
# Trailing slash important to not change hunspell.cxx
SUBST_SED.paths+=	-e 's,/usr/share/myspell/,${PREFIX}/share/hunspell/,g'

PLIST_SRC=		PLIST
PLIST_SUBST+=		DISTNAME=${DISTNAME}

REPLACE_PERL=	src/tools/ispellaff2myspell

# Build tools execute on the host; installed scripts use the target Perl.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
EMBERBSD_CROSS_BUILD_PERL?= ${TOOLBASE}/bin/perl
.if empty(EMBERBSD_CROSS_BUILD_PERL:M/*) || !exists(${EMBERBSD_CROSS_BUILD_PERL})
PKG_FAIL_REASON+= "Set EMBERBSD_CROSS_BUILD_PERL to the current host Perl"
.endif
USE_TOOLS+= perl
TOOLS_IGNORE.perl=
TOOLS_PATH.perl= ${EMBERBSD_CROSS_BUILD_PERL}
DEPENDS+= perl>=5.44.0:../../lang/perl5
REPLACE_INTERPRETER+= target-perl
REPLACE.target-perl.old= .*perl[^[:space:]]*
REPLACE.target-perl.new= ${PREFIX}/bin/perl
REPLACE_FILES.target-perl:= ${REPLACE_PERL}
REPLACE_PERL=
.else
USE_TOOLS+= perl:run
.endif

post-patch:
	cd ${WRKSRC} && ${TOOLS_PATH.autoreconf} -v -i --force

.include "../../converters/libiconv/buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../mk/curses.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
