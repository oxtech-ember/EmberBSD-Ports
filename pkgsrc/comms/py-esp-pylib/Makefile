DISTNAME= esp_pylib-1.2.0
PKGNAME= ${PYPKGPREFIX}-${DISTNAME:S/_/-/}
CATEGORIES= comms python
MASTER_SITES= ${MASTER_SITE_PYPI:=e/esp-pylib/}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/espressif/esp-pylib
COMMENT= Shared Python utilities for Espressif tools
LICENSE= apache-2.0

TOOL_DEPENDS+= ${PYPKGPREFIX}-setuptools>=70.1:../../devel/py-setuptools
DEPENDS+= ${PYPKGPREFIX}-rich-[0-9]*:../../comms/py-rich

USE_LANGUAGES= # none

.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
