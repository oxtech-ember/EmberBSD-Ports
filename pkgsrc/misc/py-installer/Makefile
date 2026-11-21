# $NetBSD: Makefile,v 1.7 2026/05/12 07:57:36 adam Exp $

DISTNAME=	installer-1.1.0
PKGREVISION=	1
PKGNAME=	${PYPKGPREFIX}-${DISTNAME}
CATEGORIES=	misc python
MASTER_SITES=	${MASTER_SITE_PYPI:=i/installer/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/pypa/installer
COMMENT=	Library for installing Python wheels
LICENSE=	mit

TEST_DEPENDS+=	${PYPKGPREFIX}-test-[0-9]*:../../devel/py-test
TEST_DEPENDS+=	${PYPKGPREFIX}-test-cov-[0-9]*:../../devel/py-test-cov
TEST_DEPENDS+=	${PYPKGPREFIX}-test-xdist-[0-9]*:../../devel/py-test-xdist

USE_LANGUAGES=	# none

PKG_OPTIONS_VAR=	PKG_OPTIONS.py-installer
PKG_SUPPORTED_OPTIONS=	windows-launchers
PKG_SUGGESTED_OPTIONS=	windows-launchers
.include "../../mk/bsd.options.mk"

PLIST_VARS+=	windows-launchers
.if !empty(PKG_OPTIONS:Mwindows-launchers)
PLIST.windows-launchers=	yes
.endif

INSTALL_ENV+=	PYTHONPATH=${WRKSRC}/src
TEST_ENV+=	PYTHONPATH=${WRKSRC}/src

# Keep pkgsrc patch backups out of the wheel and its RECORD.
pre-build:
	${RM} -f ${WRKSRC}/src/installer/*.orig
.if empty(PKG_OPTIONS:Mwindows-launchers)
	${RM} -f ${WRKSRC}/src/installer/_scripts/*.exe
.endif

do-install:
	cd ${WRKSRC} && ${SETENV} ${INSTALL_ENV} ${TOOL_PYTHONBIN} -m installer \
	    --destdir ${DESTDIR} --prefix ${PREFIX} --executable ${PYTHONBIN:Q} ${WHEELFILE}

do-test:
	cd ${WRKSRC} && ${SETENV} ${TEST_ENV} pytest-${PYVERSSUFFIX} tests

.include "../../lang/python/bootstrap.mk"
.include "../../mk/bsd.pkg.mk"
