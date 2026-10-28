# $NetBSD$
#
# EmberBSD port: sigrok-cli 0.7.2, first pkgsrc recipe. Talks to the
# libsigrok demo driver on boards without attached instruments.

DISTNAME=	sigrok-cli-0.7.2
CATEGORIES=	misc
MASTER_SITES=	https://sigrok.org/download/source/sigrok-cli/
# Fedora keeps the same upstream archive under its SHA512 in distinfo.
MASTER_SITES+=	https://src.fedoraproject.org/repo/pkgs/sigrok-cli/${DISTNAME}${EXTRACT_SUFX}/sha512/5862aa11a586ebb3acf9bffd1d2686cb5b3c3622b436080e05e2fc826a4814cf4746f128c01764f8dc664c5fc1a1e8c6ef66e548770278cc6ea99353d2173143/
EXTRACT_SUFX=	.tar.gz

MAINTAINER=	ports@emberbsd.invalid
HOMEPAGE=	https://sigrok.org/wiki/Sigrok-cli
COMMENT=	Command-line client for sigrok signal acquisition
LICENSE=	gnu-gpl-v3

GNU_CONFIGURE=	yes
USE_TOOLS+=	pkg-config gmake
USE_LANGUAGES=	c

.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/libsigrok/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
