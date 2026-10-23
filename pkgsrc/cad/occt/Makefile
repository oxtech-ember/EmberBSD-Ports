# $NetBSD$
# Origin: EmberBSD (AI-assisted), based on pkgsrc cad/occt.

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
CMAKE_REQD+=	3.10
USE_TOOLS+=	bash:run
REPLACE_BASH+=	adm/templates/draw.sh
REPLACE_BASH+=	adm/templates/custom.sh.main
REPLACE_BASH+=	adm/templates/custom.install.sh.in
REPLACE_BASH+=	adm/templates/env.install.sh.in

.include "../../mk/bsd.prefs.mk"
.include "options.mk"
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_DIR=${PREFIX}
CMAKE_CONFIGURE_ARGS+=	-DBUILD_LIBRARY_TYPE=Shared
CMAKE_CONFIGURE_ARGS+=	-DBUILD_RELEASE_DISABLE_EXCEPTIONS=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_EXPORT_COMPILE_COMMANDS=ON
CMAKE_CONFIGURE_ARGS+=	-DBUILD_USE_VCPKG=OFF
# Keep the first and repeated configure paths identical for system providers.
CMAKE_CONFIGURE_ARGS+=	-D3RDPARTY_DIR:PATH=
CMAKE_CONFIGURE_ARGS+=	-DUSE_FREETYPE=ON -DUSE_EIGEN=ON -DUSE_RAPIDJSON=ON
CMAKE_CONFIGURE_ARGS+=	-DUSE_OPENGL=ON -DUSE_FREEIMAGE=ON
CMAKE_CONFIGURE_ARGS+=	-D3RDPARTY_FREEIMAGE_DIR=${BUILDLINK_DIR}
.for module in FoundationClasses ModelingData ModelingAlgorithms Visualization ApplicationFramework DataExchange
CMAKE_CONFIGURE_ARGS+=	-DBUILD_MODULE_${module}=ON
.endfor
CMAKE_CONFIGURE_ARGS+=	-D3RDPARTY_EIGEN_INCLUDE_DIR=${BUILDLINK_DIR}/include/eigen3
CMAKE_CONFIGURE_ARGS+=	-D3RDPARTY_FREETYPE_DIR=${BUILDLINK_DIR}
CMAKE_CONFIGURE_ARGS+=	-D3RDPARTY_RAPIDJSON_DIR=${BUILDLINK_DIR}

# Preserve pkgsrc compiler and ABI selection in installed script names.
.include "../../mk/compiler.mk"
.if !empty(LP64PLATFORMS:@.PLAT.@${MACHINE_PLATFORM:M${.PLAT.}}@) || \
    (defined(ABI) && ${ABI} == "64")
.  if !empty(PKGSRC_COMPILER:Mclang)
OCCT_CUSTOM_COMPILER_DRIVER= custom_clang_64.sh
.  else
OCCT_CUSTOM_COMPILER_DRIVER= custom_gcc_64.sh
.  endif
.else
.  if !empty(PKGSRC_COMPILER:Mclang)
OCCT_CUSTOM_COMPILER_DRIVER= custom_clang_32.sh
.  else
OCCT_CUSTOM_COMPILER_DRIVER= custom_gcc_32.sh
.  endif
.endif
PLIST_SUBST+= OCCT_CUSTOM_COMPILER_DRIVER=${OCCT_CUSTOM_COMPILER_DRIVER:Q}
PLIST_SUBST+= MINOR_VERSION=${VERSION:C/.[0-9]$//}

# Use target paths in the installed shell configuration.
SUBST_CLASSES+=         custom-prefix
SUBST_STAGE.custom-prefix= post-install
SUBST_FILES.custom-prefix= ${DESTDIR}${PREFIX}/bin/${OCCT_CUSTOM_COMPILER_DRIVER}
SUBST_SED.custom-prefix= -e 's,${BUILDLINK_DIR:C|[.[\\*^]|\\\\&|gW},${PREFIX},g'

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Resolve the compiler runtime paths from the imported package location.
_OCCT_CROSS_PREFIX=     ${CROSS_DESTDIR}${PREFIX}
SUBST_CLASSES+=         cmake-prefix
SUBST_STAGE.cmake-prefix= post-install
SUBST_FILES.cmake-prefix= ${DESTDIR}${PREFIX}/lib/cmake/opencascade/OpenCASCADEConfig.cmake
SUBST_SED.cmake-prefix= -e 's,${_OCCT_CROSS_PREFIX:C|[.[\\*^]|\\\\&|gW}/,$${OpenCASCADE_INSTALL_PREFIX}/,g'
.endif

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
