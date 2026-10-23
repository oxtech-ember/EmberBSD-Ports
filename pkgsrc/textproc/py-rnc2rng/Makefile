# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted). Shared upstream Python dependency.

DISTNAME=	rnc2rng-2.7.0
PKGNAME=	${PYPKGPREFIX}-${DISTNAME}
CATEGORIES=	textproc python
MASTER_SITES=	${MASTER_SITE_PYPI:=r/rnc2rng/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/djc/rnc2rng
COMMENT=	RELAX NG Compact to XML syntax conversion library
LICENSE=	mit

TOOL_DEPENDS+=	${PYPKGPREFIX}-setuptools>=78:../../devel/py-setuptools
DEPENDS+=	${PYPKGPREFIX}-rply>=0.7.8:../../devel/py-rply

USE_LANGUAGES=	# none

PY_RENAME_BINARIES=	rnc2rng

do-test:
	cd ${WRKSRC} && ${SETENV} ${TEST_ENV} ${PYTHONBIN} test.py

.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
