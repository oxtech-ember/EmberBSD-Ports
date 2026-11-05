# $NetBSD$
# Origin: mat007/turtle v2.0.0 (2a54301cc3c5bb48c850913e15a6264f8140e86d)
DISTNAME=	turtle-2.0.0
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=mat007/}
GITHUB_PROJECT=	turtle
GITHUB_TAG=	v${PKGVERSION_NOREV}
WRKSRC=		${WRKDIR}/turtle-${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/mat007/turtle
COMMENT=	C++ mock-object library
LICENSE=	boost-license
USE_LANGUAGES=	c++
NO_ARCH=	yes

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DTURTLE_INSTALL:BOOL=ON

INSTALLATION_DIRS+=	share/licenses/turtle
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE_1_0.txt ${DESTDIR}${PREFIX}/share/licenses/turtle/LICENSE_1_0.txt

.include "../../devel/boost-headers/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
