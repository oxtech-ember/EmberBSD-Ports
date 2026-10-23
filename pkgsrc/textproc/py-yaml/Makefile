# $NetBSD: Makefile,v 1.40 2026/06/28 15:41:43 wiz Exp $
# Origin: EmberBSD (AI-assisted), require the real current Cython/libyaml extension.

DISTNAME=	pyyaml-6.0.3
PKGREVISION=	1
PKGNAME=	${PYPKGPREFIX}-${DISTNAME:S/py//}
CATEGORIES=	textproc python
MASTER_SITES=	${MASTER_SITE_PYPI:=P/PyYAML/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/yaml/pyyaml
COMMENT=	Collection of libraries to process YAML with Python
LICENSE=	mit

TOOL_DEPENDS+=	${PYPKGPREFIX}-cython>=3.3.0:../../devel/py-cython
TOOL_DEPENDS+=	${PYPKGPREFIX}-setuptools>=78:../../devel/py-setuptools

# The old pkgsrc patch disabled Cython and silently lost the C extension.
MAKE_ENV+=	PYYAML_FORCE_CYTHON=1 PYYAML_FORCE_LIBYAML=1

PYTHON_VERSIONS_INCOMPATIBLE=	310 311

.include "../../lang/python/wheel.mk"
.include "../../textproc/libyaml/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
