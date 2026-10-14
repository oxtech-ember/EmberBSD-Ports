# EmberBSD: Cryptodome flavour of pycryptodome (mtkclient dep).
DISTNAME=	pycryptodomex-3.24.1
PKGNAME=	${PYPKGPREFIX}-${DISTNAME:S/^py//}
CATEGORIES=	security python
MASTER_SITES=	${MASTER_SITE_PYPI:=p/pycryptodomex/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.pycryptodome.org/
COMMENT=	Cryptographic and hash functions for Python (Cryptodome flavour)
LICENSE=	public-domain AND python-software-foundation

# "error: 'for' loop initial declarations are only allowed in C99 mode"
FORCE_C_STD=	c99
CHECK_PORTABILITY_SKIP=	appveyor/get_wheels.sh

.include "../../lang/python/egg.mk"

# Python 3 builds of this package get an extra "abi3" suffix added
.if ${PYTHON_VERSION} < 300
PLIST_SUBST+=	SOEXT="so"
.else
PLIST_SUBST+=	SOEXT="abi3.so"
.endif

# EmberBSD: the host build interpreter names stable-ABI extensions with
# its own platform tag (for example abi3-darwin); rename them to the
# target convention during cross builds.
.if defined(USE_CROSS_COMPILE) && ${USE_CROSS_COMPILE:tl} == "yes"
post-install:
	find ${DESTDIR}${PREFIX} -name '*.abi3-*.so' -exec sh -c 'mv "$$1" "$${1%.abi3-*.so}.abi3.so"' _ {} \;
.endif

BUILDLINK_API_DEPENDS.gmp+=	gmp>=5.0
.include "../../devel/gmp/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
