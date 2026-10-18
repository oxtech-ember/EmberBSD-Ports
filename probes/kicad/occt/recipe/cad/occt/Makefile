# $NetBSD$
# Origin: EmberBSD (AI-assisted), based on pkgsrc cad/occt.
# Source checkpoint: derive and review static PLIST from the full stage.

VERSION=	8.0.1
DISTNAME=	OCCT-${VERSION}
PKGNAME=	occt-${VERSION}
CATEGORIES=	cad
MASTER_SITES=	${MASTER_SITE_GITHUB:=Open-Cascade-SAS/}
GITHUB_PROJECT=	OCCT
GITHUB_TAG=	V${VERSION}
WRKSRC=		${WRKDIR}/OCCT-${VERSION}
PATCH_STRIP=	-p1

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://dev.opencascade.org/
COMMENT=	Boundary Representation modeling toolkit and 3D geometry library
LICENSE=	gnu-lgpl-v2.1
# Source retains OCCT_LGPL_EXCEPTION.txt and its commercial-license alternative.
USE_LANGUAGES=	c c++
USE_CXX_FEATURES=	c++17
GCC_REQD+=	16.2
CMAKE_REQD+=	4.4.4
USE_TOOLS+=	bash
DEPENDS+=	bash>=5.3:../../shells/bash
REPLACE_BASH+=	adm/templates/draw.sh

.include "../../mk/bsd.prefs.mk"
.include "options.mk"
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_DIR=${PREFIX}
CMAKE_CONFIGURE_ARGS+=	-DBUILD_LIBRARY_TYPE=Shared
CMAKE_CONFIGURE_ARGS+=	-DBUILD_RELEASE_DISABLE_EXCEPTIONS=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_EXPORT_COMPILE_COMMANDS=ON
CMAKE_CONFIGURE_ARGS+=	-DBUILD_USE_VCPKG=OFF
CMAKE_CONFIGURE_ARGS+=	-DUSE_FREETYPE=ON -DUSE_EIGEN=ON -DUSE_RAPIDJSON=ON
CMAKE_CONFIGURE_ARGS+=	-DUSE_OPENGL=ON -DUSE_FREEIMAGE=ON
CMAKE_CONFIGURE_ARGS+=	-D3RDPARTY_FREEIMAGE_DIR=${BUILDLINK_DIR}
.for module in FoundationClasses ModelingData ModelingAlgorithms Visualization ApplicationFramework DataExchange
CMAKE_CONFIGURE_ARGS+=	-DBUILD_MODULE_${module}=ON
.endfor
CMAKE_CONFIGURE_ARGS+=	-D3RDPARTY_EIGEN_INCLUDE_DIR=${BUILDLINK_DIR}/include/eigen3
CMAKE_CONFIGURE_ARGS+=	-D3RDPARTY_FREETYPE_DIR=${BUILDLINK_DIR}
CMAKE_CONFIGURE_ARGS+=	-D3RDPARTY_RAPIDJSON_DIR=${BUILDLINK_DIR}

SUBST_CLASSES+=		unbl3
SUBST_STAGE.unbl3=	post-build
SUBST_FILES.unbl3=	${CMAKE_BUILD_DIR}/CMakeFiles/Export/*/*.cmake
SUBST_SED.unbl3=	-e 's,${BUILDLINK_DIR},${PREFIX},g'
SUBST_MESSAGE.unbl3=	Fix paths to buildlink directories in installed files.

.include "../../devel/cmake/build.mk"
.include "../../fonts/fontconfig/buildlink3.mk"
.include "../../graphics/freetype2/buildlink3.mk"
BUILDLINK_API_DEPENDS.freeimage+=	freeimage>=3.19.25nb3
.include "../../graphics/freeimage/buildlink3.mk"
BUILDLINK_API_DEPENDS.eigen3+=	eigen3>=5.0.1
.include "../../math/eigen3/buildlink3.mk"
BUILDLINK_API_DEPENDS.rapidjson+=	rapidjson>=1.1.0.20250205nb1
.include "../../textproc/rapidjson/buildlink3.mk"
.include "../../textproc/expat/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
