# $NetBSD: Makefile,v 1.29 2026/08/30 15:42:59 wiz Exp $

DISTNAME=	wcwidth-0.9.4
PKGNAME=	${PYPKGPREFIX}-${DISTNAME}
CATEGORIES=	devel python
MASTER_SITES=	${MASTER_SITE_PYPI:=w/wcwidth/}

MAINTAINER=	kamelderouiche@yahoo.com
HOMEPAGE=	https://github.com/jquast/wcwidth
COMMENT=	Measures number of Terminal column cells of wide-character codes
LICENSE=	mit

TOOL_DEPENDS+=	${PYPKGPREFIX}-setuptools>=61:../../devel/py-setuptools
TEST_DEPENDS+=	${PYPKGPREFIX}-test-cov>=0:../../devel/py-test-cov

USE_LANGUAGES=	# none
MAKE_ENV+=	WCWIDTH_NO_EXTENSION=1

# as of 0.8.3
# 1 failed, 1363 passed, 10 skipped
# after installation, no errors

.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
