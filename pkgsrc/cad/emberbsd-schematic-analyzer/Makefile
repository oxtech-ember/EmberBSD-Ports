# $NetBSD$

DISTNAME=	EmberBSD-Schematic-Analyzer-0.1.0
PKGNAME=	${DISTNAME:tl}
WHEEL_NAME=	emberbsd_schematic_analyzer-${PKGVERSION_NOREV}
CATEGORIES=	cad
MASTER_SITES=	${MASTER_SITE_GITHUB:=oxtech-ember/}
GITHUB_PROJECT=	EmberBSD-Schematic-Analyzer
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/oxtech-ember/EmberBSD-Schematic-Analyzer
COMMENT=	Read-only electrical and drawing analysis of KiCad schematics
LICENSE=	gnu-gpl-v3

TOOL_DEPENDS+=	${PYPKGPREFIX}-setuptools>=77:../../devel/py-setuptools
DEPENDS+=	${PYPKGPREFIX}-kiutils>=1.4.8nb1:../../cad/py-kiutils
DEPENDS+=	kicad>=10.0.8:../../cad/kicad10

USE_LANGUAGES=	# none
USE_PYTEST=	no
PYTHON_VERSIONS_INCOMPATIBLE=	27 38 39 310

do-test:
	${RUN} cd ${WRKSRC} && ${SETENV} ${TEST_ENV} PYTHONPATH=${WRKSRC}/src \
		${TOOL_PYTHONBIN} -m unittest discover -s tests -v

.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
