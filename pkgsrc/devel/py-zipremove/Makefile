DISTNAME= zipremove-0.10.0
PKGNAME= ${PYPKGPREFIX}-${DISTNAME:S/_/-/}
CATEGORIES= devel python
MASTER_SITES= ${MASTER_SITE_PYPI:=z/zipremove/}
HOMEPAGE= https://pypi.org/project/zipremove/
COMMENT= Python zipremove package
LICENSE= mit
TOOL_DEPENDS+= ${PYPKGPREFIX}-setuptools>=61:../../devel/py-setuptools

USE_LANGUAGES= # none
.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
