# EmberBSD: FUSE ctypes bindings for libfuse 2 and 3 (mtkclient dep).
DISTNAME=	mfusepy-3.1.1
PKGNAME=	${PYPKGPREFIX}-${DISTNAME}
CATEGORIES=	filesystems python
MASTER_SITES=	${MASTER_SITE_PYPI:=m/mfusepy/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/mhfuse/mfusepy
COMMENT=	Ctypes bindings for the high-level API in libfuse 2 and 3
LICENSE=	isc

TOOL_DEPENDS+=	${PYPKGPREFIX}-setuptools-[0-9]*:../../devel/py-setuptools
TOOL_DEPENDS+=	${PYPKGPREFIX}-wheel-[0-9]*:../../devel/py-wheel
# libfuse is dlopen'ed at runtime via ctypes; install the fuse package on
# the target to enable the FUSE-backed dump commands.

.include "../../lang/python/wheel.mk"
.include "../../mk/bsd.pkg.mk"
