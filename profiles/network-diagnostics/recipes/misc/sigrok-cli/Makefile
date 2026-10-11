# $NetBSD$
#
# EmberBSD port: sigrok-cli 0.7.2, first pkgsrc recipe. Talks to the
# libsigrok demo driver on boards without attached instruments.

DISTNAME=	sigrok-cli-0.7.2
CATEGORIES=	misc
MASTER_SITES=	https://sigrok.org/download/source/sigrok-cli/
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
