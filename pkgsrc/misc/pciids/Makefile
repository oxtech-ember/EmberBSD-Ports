# EmberBSD: current upstream PCI ID data snapshot.
DISTNAME=	pci.ids
PKGNAME=	pciids-20261121
CATEGORIES=	misc
MASTER_SITES=	${MASTER_SITE_GITHUB:=pciutils/}
GITHUB_PROJECT=	pciids
GITHUB_TAG=	bc2920f3fc38e42d0aecc8ce4b17d1ed034dbd70
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

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	1	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"
