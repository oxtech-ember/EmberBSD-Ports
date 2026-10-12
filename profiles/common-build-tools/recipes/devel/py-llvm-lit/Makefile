# Origin: EmberBSD common profile, AI-assisted packaging of upstream lit.
.include "../../lang/llvm/version.mk"

PKGNAME= ${PYPKGPREFIX}-llvm-lit-${LLVM_VERSION}
CATEGORIES= devel python
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://llvm.org/docs/CommandGuide/lit.html
COMMENT= LLVM integrated testing module and installed launcher
LICENSE= apache-2.0

WRKSRC= ${WRKDIR}/${DISTNAME}/llvm/utils/lit
EXTRACT_ELEMENTS= ${DISTNAME}/llvm/utils/lit
WHEEL_NAME= lit-23.1.3.dev0
PYTHON_VERSIONS_ACCEPTED= 314
USE_LANGUAGES= # none
USE_PYTEST= no
REPLACE_PYTHON+= lit.py
INSTALLATION_DIRS+= bin
TOOL_DEPENDS+= ${PYPKGPREFIX}-setuptools>=0:../../devel/py-setuptools

post-install:
	${INSTALL_SCRIPT} ${WRKSRC}/lit.py ${DESTDIR}${PREFIX}/bin/llvm-lit

.include "../../lang/python/application.mk"
.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
