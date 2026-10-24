# $NetBSD: Makefile,v 1.2 2025/05/27 16:55:49 schmonz Exp $

DISTNAME=		prettyping-1.1.0
CATEGORIES=		net
MASTER_SITES=		${MASTER_SITE_GITHUB:=denilsonsa/}
GITHUB_TAG=		v${PKGVERSION_NOREV}
PKGREVISION=		1

MAINTAINER=		schmonz@NetBSD.org
HOMEPAGE=		https://github.com/denilsonsa/prettyping/
COMMENT=		Wrapper to colorize and simplify ping's output
LICENSE=		mit

USE_LANGUAGES=		# none
NO_BUILD=		yes

USE_TOOLS+=		bash:run
# REPLACE_BASH uses the target Bash path in cross builds.
REPLACE_BASH=		${PKGBASE}

INSTALLATION_DIRS=	bin

do-install:
	${INSTALL_SCRIPT} ${WRKSRC}/${PKGBASE} ${DESTDIR}${PREFIX}/bin

.include "../../mk/bsd.pkg.mk"
