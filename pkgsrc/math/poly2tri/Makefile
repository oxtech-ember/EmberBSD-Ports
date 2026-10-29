# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted); common poly2tri provider.
DISTNAME=	poly2tri-0.0.20261020
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=jhasse/}
GITHUB_TAG=	4732e46da88086c6b7b3935a5b4f6f87360062c3
WRKSRC=		${WRKDIR}/poly2tri-${GITHUB_TAG}
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/jhasse/poly2tri/
COMMENT=	2D constrained Delaunay triangulation library
LICENSE=	modified-bsd
USE_LANGUAGES=	c c++
USE_CXX_FEATURES=	c++14

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+=	libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+=	EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
INSTALLATION_DIRS+=	share/doc/poly2tri
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/doc/poly2tri/LICENSE
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
