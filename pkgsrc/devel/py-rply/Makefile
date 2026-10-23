# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted). Shared upstream Python dependency.

DISTNAME=	rply-0.7.8
PKGNAME=	${PYPKGPREFIX}-${DISTNAME}
CATEGORIES=	devel python
MASTER_SITES=	${MASTER_SITE_PYPI:=r/rply/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/alex/rply
COMMENT=	Pure Python Lex and Yacc parser generator
LICENSE=	modified-bsd

TOOL_DEPENDS+=	${PYPKGPREFIX}-setuptools>=78:../../devel/py-setuptools
DEPENDS+=	${PYPKGPREFIX}-appdirs>=1.4.4:../../devel/py-appdirs

USE_LANGUAGES=	# none

.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
