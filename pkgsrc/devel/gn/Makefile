# $NetBSD$

DISTNAME=	gn-2610
CATEGORIES=	devel
GN_REVISION=	84f10d13f9041068a7da8f9dfc9b991e1049823a
GN_TREE=	dd53ce1ebf874ac04939e5684fc39e81d87c2008
MASTER_SITES=	https://gn.googlesource.com/gn/+archive/
DISTFILES=	gn-${GN_REVISION}.tar

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gn.googlesource.com/gn/
COMMENT=	Meta-build system that generates Ninja build files
LICENSE=	modified-bsd

# Current upstream GN; Chromium 156 pin is an ancestor.
# The GN initial-commit tag gives initial-commit-2610-g84f10d13.
GN_VERSION=	2610 (84f10d13f904)
WRKSRC=		${WRKDIR}/${DISTNAME}
EXTRACT_DIR=	${WRKSRC}

USE_LANGUAGES=		c++
USE_CXX_FEATURES=	c++23
ONLY_FOR_COMPILER=	clang gcc
USE_TOOLS+=		rm
TOOL_DEPENDS+=		ninja-build>=1.13.2:../../devel/ninja-build
TOOL_DEPENDS+=		cxxbridge-1.0.205{,nb[0-9]*}:../../devel/cxxbridge
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
GN_ENV+=		GN_CXX_INCLUDE=${WRKDIR:Q}/gn-cxx-include

INSTALLATION_DIRS=	bin share/doc/gn

# Gitiles injects request-time PAX mtimes, so its tar.gz bytes are unstable.
# This source-only control Python need not be part of a complete build SDK.
GN_FETCH_PYTHON?=	${TOOL_PYTHONBIN}
BUILD_DEFS+=		EMBERBSD_SDK_SOURCE

do-fetch: error-check
	${RUN} set -e; \
	if ${TEST} ! -f ${DISTDIR:Q}/${DIST_SUBDIR:Q}/${DISTFILES:Q}; then \
	    case ${GN_FETCH_PYTHON:Q} in \
	    /*) ;; \
	    *) ${FAIL_MSG} "Set GN_FETCH_PYTHON to an absolute control Python executable" ;; \
	    esac; \
	    case x${EMBERBSD_SDK_SOURCE:Q} in \
	    x/*) ;; \
	    *) ${FAIL_MSG} "Set EMBERBSD_SDK_SOURCE to the SDK source code" ;; \
	    esac; \
	    ${GN_FETCH_PYTHON:Q} -B -I -S ${FILESDIR:Q}/fetch-source.py \
	        --sdk-source ${EMBERBSD_SDK_SOURCE:Q} \
	        --revision ${GN_REVISION:Q} --tree ${GN_TREE:Q} \
	        --output ${DISTDIR:Q}/${DIST_SUBDIR:Q}/${DISTFILES:Q}; \
	fi

do-configure:
	${RUN} ${MKDIR} ${WRKDIR:Q}/gn-cxx-include/rust
	${RUN} ${CP} ${TOOLBASE:Q}/include/rust/cxx.h ${WRKDIR:Q}/gn-cxx-include/rust/cxx.h
	${RUN} ${TOOLBASE:Q}/bin/cxxbridge --header > ${WRKDIR:Q}/cxx-generated.h
	${RUN} ${CMP} ${WRKDIR:Q}/cxx-generated.h ${WRKDIR:Q}/gn-cxx-include/rust/cxx.h
	${RUN} ${TOOLBASE:Q}/bin/cxxbridge ${WRKSRC:Q}/src/gn/starlark/crates/ffi/src/bridge.rs --header > ${WRKSRC:Q}/src/gn/ffi/bridge.h
	${RUN} ${TOOLBASE:Q}/bin/cxxbridge ${WRKSRC:Q}/src/gn/starlark/crates/ffi/src/bridge.rs > ${WRKSRC:Q}/src/gn/ffi/bridge.cc
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
