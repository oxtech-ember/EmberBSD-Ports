# $NetBSD$
# Origin: KiCad 10.0.8 thirdparty/3dxware_sdk, 3Dconnexion 3DxWare SDK v4 subset.
DISTNAME=	3dxware-sdk-4.0
CATEGORIES=	devel
MASTER_SITES=	https://gitlab.com/kicad/code/kicad/-/archive/10.0.8/
DISTFILES=	kicad-10.0.8.tar.bz2
SITES.kicad-10.0.8.tar.bz2=	${MASTER_SITES}
WRKSRC=	${WRKDIR}/kicad-10.0.8/thirdparty/3dxware_sdk

EXTRACT_ELEMENTS+=	kicad-10.0.8/thirdparty/3dxware_sdk/inc
EXTRACT_ELEMENTS+=	kicad-10.0.8/thirdparty/3dxware_sdk/src/navlib_stub.c
EXTRACT_ELEMENTS+=	kicad-10.0.8/thirdparty/3dxware_sdk/src/navlib_load.cpp
EXTRACT_ELEMENTS+=	kicad-10.0.8/LICENSE.GPLv3

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://3dconnexion.com/software-developer-program/
COMMENT=	KiCad-maintained GPL subset of the 3Dconnexion navigation API
LICENSE=	gnu-gpl-v3
USE_LANGUAGES=	c c++

post-extract:
	${CP} ${FILESDIR}/CMakeLists.txt ${WRKSRC}/CMakeLists.txt
	${CP} ${FILESDIR}/TDxWare_SDKConfig.cmake.in ${WRKSRC}/TDxWare_SDKConfig.cmake.in

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_INCLUDEDIR=include
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib

INSTALLATION_DIRS+=	share/licenses/3dxware-sdk
post-install:
	${INSTALL_DATA} ${WRKDIR}/kicad-10.0.8/LICENSE.GPLv3 ${DESTDIR}${PREFIX}/share/licenses/3dxware-sdk/LICENSE.GPLv3

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
