# $NetBSD$

DISTNAME=	gn-2486
CATEGORIES=	devel
GN_REVISION=	641ace93dd9560e75e7add0d08f77b446fbb3b78
MASTER_SITES=	https://gn.googlesource.com/gn/+archive/
DISTFILES=	${GN_REVISION}.tar.gz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gn.googlesource.com/gn/
COMMENT=	Meta-build system that generates Ninja build files
LICENSE=	modified-bsd

# Published Chromium tag 152.0.7977.167 pins this commit in DEPS.
# The GN initial-commit tag gives initial-commit-2486-g641ace93dd95.
GN_VERSION=	2486 (641ace93dd95)
WRKSRC=		${WRKDIR}/${DISTNAME}
EXTRACT_DIR=	${WRKSRC}

USE_LANGUAGES=		c++
USE_CXX_FEATURES=	c++23
ONLY_FOR_COMPILER=	gcc
GCC_REQD+=		16.2
USE_TOOLS+=		rm
TOOL_DEPENDS+=		ninja-build>=1.13.2:../../devel/ninja-build
PYTHON_VERSIONS_ACCEPTED=	315
PYTHON_FOR_BUILD_ONLY=	tool
HAS_CONFIGURE=		yes

.include "../../mk/bsd.prefs.mk"

# The target compiler stays separate from the native Python and Ninja tools.
GN_NINJA=		${TOOLBASE}/bin/ninja
GN_CXXFLAGS=		${CPPFLAGS} ${CXXFLAGS}
# Apply these bindings after pkgsrc ALL_ENV, including during regeneration.
GN_ENV=			AR=${AR:Q} CXX=${CXX:Q}
GN_ENV+=		CFLAGS= CXXFLAGS=${GN_CXXFLAGS:Q} LDFLAGS=${LDFLAGS:Q}
GN_ENV+=		GN_VERSION=${GN_VERSION:Q}

INSTALLATION_DIRS=	bin share/doc/gn

do-configure:
	cd ${WRKSRC} && ${SETENV} ${CONFIGURE_ENV} ${GN_ENV} ${TOOL_PYTHONBIN} \
	    build/gen.py --platform ${LOWER_OPSYS:Q} --host ${NATIVE_LOWER_OPSYS:Q}

# Each invocation has one executable link. Parallel compilation is retained.
do-build:
	cd ${WRKSRC} && ${SETENV} ${MAKE_ENV} ${GN_ENV} \
	    ${GN_NINJA} -C out -j ${_MAKE_JOBS_N} gn

do-test:
	cd ${WRKSRC} && ${SETENV} ${MAKE_ENV} ${GN_ENV} \
	    ${GN_NINJA} -C out -j ${_MAKE_JOBS_N} gn_unittests
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${FAIL_MSG} "Run out/gn_unittests on the target. Do not execute it on the build host."
.else
	cd ${WRKSRC} && ${SETENV} ${TEST_ENV} out/gn_unittests
.endif

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/out/gn ${DESTDIR}${PREFIX}/bin
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${WRKSRC}/README.md \
	    ${DESTDIR}${PREFIX}/share/doc/gn

.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
