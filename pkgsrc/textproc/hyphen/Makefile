# $NetBSD: Makefile,v 1.14 2025/08/25 08:35:12 wiz Exp $

DISTNAME=	hyphen-2.8.9
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=hunspell/}
GITHUB_PROJECT=	hyphen
GITHUB_RELEASE=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/hunspell/hyphen
COMMENT=	Library for high quality hyphenation and justification
LICENSE=	mpl-1.1 OR gnu-lgpl-v2.1 OR gnu-gpl-v2

USE_LIBTOOL=	yes
USE_TOOLS+=	gawk patch perl bash:test
GNU_CONFIGURE=	yes

REPLACE_PERL=	substrings.pl
REPLACE_BASH=	tests/test.sh
TEST_TARGET=	check

.include "../../mk/bsd.prefs.mk"

# Perl runs on the build host to generate dictionaries. The installed
# helper needs Perl at runtime. Preserve the existing cross library payload.
PLIST_VARS+=	substrings
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PLIST.substrings= yes
USE_TOOLS+=	perl:run
.else
SUBST_CLASSES+=	cross
SUBST_STAGE.cross=	pre-configure
SUBST_FILES.cross=	Makefile.in
SUBST_SED.cross+=	-e 's,^bin_SCRIPTS = substrings.pl,bin_SCRIPTS =,'
SUBST_MESSAGE.cross=	Keep the existing cross package without the Perl runtime helper.
.endif

.include "../../mk/bsd.pkg.mk"
