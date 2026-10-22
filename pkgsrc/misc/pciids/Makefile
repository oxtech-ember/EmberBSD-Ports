# EmberBSD: current upstream PCI ID data snapshot.
DISTNAME=	pci.ids
PKGNAME=	pciids-20261022
CATEGORIES=	misc
MASTER_SITES=	${MASTER_SITE_GITHUB:=pciutils/}
GITHUB_PROJECT=	pciids
GITHUB_TAG=	86e7077e4b7947be28d4de891c69f7ae64da0286
WRKSRC=		${WRKDIR}/pciids-${GITHUB_TAG}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://pci-ids.ucw.cz/
COMMENT=	Current snapshot of the PCI ID database
LICENSE=	modified-bsd OR gnu-gpl-v2

INSTALLATION_DIRS=	share/pciids
USE_LANGUAGES=	# none
NO_CONFIGURE=	yes
NO_BUILD=	yes

do-install:
	${INSTALL_DATA} ${WRKSRC}/pci.ids ${DESTDIR}${PREFIX}/share/pciids

.include "../../mk/bsd.pkg.mk"
