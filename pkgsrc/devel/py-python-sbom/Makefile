DISTNAME= python_sbom-0.5.0
PKGNAME= ${PYPKGPREFIX}-${DISTNAME:S/_/-/}
CATEGORIES= devel python
MASTER_SITES= ${MASTER_SITE_PYPI:=p/python-sbom/}
HOMEPAGE= https://pypi.org/project/python-sbom/
COMMENT= Python python-sbom package
LICENSE= mit AND apache-2.0
TOOL_DEPENDS+= ${PYPKGPREFIX}-hatchling>=1.32.4:../../devel/py-hatchling
TOOL_DEPENDS+= ${PYPKGPREFIX}-hatch-vcs>=0.5:../../devel/py-hatch-vcs
TOOL_DEPENDS+= ${PYPKGPREFIX}-hatch-fancy-pypi-readme>=25.1:../../devel/py-hatch-fancy-pypi-readme
DEPENDS+= ${PYPKGPREFIX}-installer>=1.1:../../misc/py-installer
DEPENDS+= ${PYPKGPREFIX}-packageurl>=0.11.1:../../devel/py-packageurl
DEPENDS+= ${PYPKGPREFIX}-packaging>=26.3:../../devel/py-packaging
DEPENDS+= ${PYPKGPREFIX}-zipremove>=0.10:../../devel/py-zipremove
TOOL_DEPENDS+= ${PYPKGPREFIX}-installer>=1.1:../../misc/py-installer
TOOL_DEPENDS+= ${PYPKGPREFIX}-packageurl>=0.11.1:../../devel/py-packageurl
TOOL_DEPENDS+= ${PYPKGPREFIX}-zipremove>=0.10:../../devel/py-zipremove

USE_LANGUAGES= # none
PY_RENAME_BINARIES= python-sbom
.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
