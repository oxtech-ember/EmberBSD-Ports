# $NetBSD$

DISTNAME=	estree-1.0.9
PKGNAME=	node-types-${DISTNAME}
CATEGORIES=	devel
MASTER_SITES=	https://registry.npmjs.org/@types/estree/-/
EXTRACT_SUFX=	.tgz
WRKSRC=		${WRKDIR}/estree

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/estree
COMMENT=	TypeScript declarations for ESTree JavaScript syntax trees
LICENSE=	mit

NO_BUILD=	yes
USE_LANGUAGES=	# none
INSTALLATION_DIRS=	lib/node_modules/@types/estree

do-install:
.for file in LICENSE README.md flow.d.ts index.d.ts package.json
	${INSTALL_DATA} ${WRKSRC}/${file} ${DESTDIR}${PREFIX}/lib/node_modules/@types/estree/${file}
.endfor

.include "../../mk/bsd.pkg.mk"
