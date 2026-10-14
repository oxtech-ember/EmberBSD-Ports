# EmberBSD: Mediatek BROM/DA client for legal flashing of one's own
# devices (phone rescue kit, R16).
DISTNAME=	mtkclient-2.1.4.1
CATEGORIES=	comms python
MASTER_SITES=	${MASTER_SITE_GITHUB:=bkerler/}
GITHUB_PROJECT=	mtkclient
GITHUB_TAG=	v${PKGVERSION_NOREV}
WRKSRC=		${WRKDIR}/mtkclient-${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/bkerler/mtkclient
COMMENT=	Mediatek reverse engineering and flashing tools
LICENSE=	gnu-gpl-v3

TOOL_DEPENDS+=	${PYPKGPREFIX}-hatchling-[0-9]*:../../devel/py-hatchling

DEPENDS+=	${PYPKGPREFIX}-usb-[0-9]*:../../devel/py-usb
DEPENDS+=	${PYPKGPREFIX}-cryptodome>=3.23:../../security/py-cryptodome
DEPENDS+=	${PYPKGPREFIX}-cryptodomex>=3.24:../../local-phone/py-pycryptodomex
DEPENDS+=	${PYPKGPREFIX}-colorama-[0-9]*:../../comms/py-colorama
DEPENDS+=	${PYPKGPREFIX}-serial-[0-9]*:../../comms/py-serial
# capstone/keystone are optional at runtime (guarded imports); cross
# C-extension python packaging for them is tracked as a separate debt.
DEPENDS+=	${PYPKGPREFIX}-mfusepy-[0-9]*:../../local-phone/py-mfusepy

# The GUI entry point stays installed as upstream ships it; the heavy
# Qt dependencies (pyside6, shiboken6) are out of scope for the CLI kit.
# mtk_gui needs them installed separately if ever required.

USE_LANGUAGES=	# none

REPLACE_PYTHON+=	mtk.py mtk_gui.py stage2.py
REPLACE_PYTHON+=	Tools/*.py

# The wheel force-includes some top-level scripts verbatim; normalize
# their shebangs after staging.
post-install:
	find ${DESTDIR}${PREFIX} -path '*site-packages/mtkclient*' \
		\( -name '*.py' -exec sed -i '1s|^#!.*python.*|#!${PYTHONBIN}|' {} + \
		-o -name '*.sh' -exec sed -i '1s|^#!.*sh.*|#!/bin/sh|' {} + \)
PYTHON_VERSIONS_INCOMPATIBLE=	27

.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
