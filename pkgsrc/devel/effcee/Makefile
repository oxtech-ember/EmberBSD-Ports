# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted); current tested upstream sources.
DISTNAME=	effcee-1.2026.0
PKGREVISION=	2
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 3
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
DEPENDS+= abseil>=20260817.0nb4:../../devel/abseil
DEPENDS+= re2>=20251105nb4:../../devel/re2
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=google/}
GITHUB_TAG=	f8e8a164822d4f65e757bff66bc00e1567959aa0

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/google/effcee
COMMENT=	C++ library for stateful diagnostic pattern matching
LICENSE=	apache-2.0

WRKSRC=		${WRKDIR}/effcee-${GITHUB_TAG}
USE_LANGUAGES=	c c++
USE_CXX_FEATURES+= c++17
PYTHON_FOR_BUILD_ONLY=	tool
PYTHON_VERSION_REQD=	315

CMAKE_CONFIGURE_ARGS+= -DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DEFFCEE_USE_INSTALLED_DEPS=ON
CMAKE_CONFIGURE_ARGS+= -DEFFCEE_BUILD_TESTING=ON
CMAKE_CONFIGURE_ARGS+= -DEFFCEE_BUILD_SAMPLES=ON
CMAKE_CONFIGURE_ARGS+= -DPython3_EXECUTABLE=${TOOL_PYTHONBIN:Q}
TEST_TARGET=	test

.include "../../devel/cmake/build.mk"

# Run native tests before the package installs its shared library.
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
TEST_ENV+= LD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/effcee
TEST_ENV+= DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/effcee
.endif

.include "../../lang/python/tool.mk"
BUILDLINK_API_DEPENDS.re2+= re2>=20251105nb3
.include "../../devel/re2/buildlink3.mk"
.include "../../devel/abseil/buildlink3.mk"
BUILDLINK_API_DEPENDS.googletest+= googletest>=1.18.0
BUILDLINK_DEPMETHOD.googletest= build
.include "../../devel/googletest/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
