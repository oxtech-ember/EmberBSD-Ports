# $NetBSD$
# Origin: mat007/turtle v2.0.0 (2a54301cc3c5bb48c850913e15a6264f8140e86d)
DISTNAME=\tturtle-2.0.0
CATEGORIES=\tdevel
MASTER_SITES=\t${MASTER_SITE_GITHUB:=mat007/}
GITHUB_PROJECT=\tturtle
GITHUB_TAG=\tv${PKGVERSION_NOREV}
WRKSRC=\t\t${WRKDIR}/turtle-${PKGVERSION_NOREV}

MAINTAINER=\tpkgsrc-users@NetBSD.org
HOMEPAGE=\thttps://github.com/mat007/turtle
COMMENT=\tC++ mock-object library
LICENSE=\tboost-license
USE_LANGUAGES=\tc++
NO_ARCH=	yes

CMAKE_CONFIGURE_ARGS+=\t-DBUILD_TESTING:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=\t-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=\t-DTURTLE_INSTALL:BOOL=ON

INSTALLATION_DIRS+=\tshare/licenses/turtle
post-install:
\t${INSTALL_DATA} ${WRKSRC}/LICENSE_1_0.txt ${DESTDIR}${PREFIX}/share/licenses/turtle/LICENSE_1_0.txt

.include "../../devel/boost-headers/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
