# Python ISA simulator and compiler for openTPU.
DISTNAME=	opentpu-0.1.0
PKGNAME=	${PYPKGPREFIX}-${DISTNAME}
CATEGORIES=	python
MASTER_SITES=	${MASTER_SITE_GITHUB:=FeSens/}
GITHUB_PROJECT=	openTPU
GITHUB_TAG=	730ca28feb77b5598090e97ab209f302f0c56eec
WRKSRC=		${WRKDIR}/openTPU-${GITHUB_TAG}

HOMEPAGE=	https://github.com/FeSens/openTPU
COMMENT=	Python ISA simulator and compiler for openTPU
MAINTAINER=	pkgsrc-users@NetBSD.org
LICENSE=	apache-2.0

USE_LANGUAGES=	none
GCC_REQD+=	16.2
USE_PYTEST=	no

TOOL_DEPENDS+=	${PYPKGPREFIX}-setuptools>=70.1:../../devel/py-setuptools
DEPENDS+=	${PYPKGPREFIX}-numpy-[0-9]*:../../math/py-numpy

INSTALLATION_DIRS+=	share/doc/${PKGBASE}

post-install:
	${INSTALL_DATA} ${FILESDIR}/SOURCE ${DESTDIR}${PREFIX}/share/doc/${PKGBASE}/SOURCE

.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
