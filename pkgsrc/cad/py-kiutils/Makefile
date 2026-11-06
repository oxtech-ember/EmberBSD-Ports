# $NetBSD$

DISTNAME=	kiutils-1.4.8
PKGNAME=	${PYPKGPREFIX}-${DISTNAME}
PKGREVISION=	1
CATEGORIES=	cad python
MASTER_SITES=	${MASTER_SITE_PYPI:=k/kiutils/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/mvnmgrx/kiutils
COMMENT=	Python model and parser for KiCad design files
LICENSE=	gnu-gpl-v3

TOOL_DEPENDS+=	${PYPKGPREFIX}-setuptools>=70.1:../../devel/py-setuptools
USE_LANGUAGES=	# none
USE_PYTEST=	no

do-test:
	${RUN}${SETENV} ${TEST_ENV} PYTHONPATH=${WRKSRC}/src \
		${TOOL_PYTHONBIN} ${FILESDIR}/test-junction.py

.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
