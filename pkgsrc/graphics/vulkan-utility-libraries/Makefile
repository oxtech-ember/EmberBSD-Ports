# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).

DISTNAME=	vulkan-utility-libraries-1.4.363.0
CATEGORIES=	graphics
EXTRACT_USING=	bsdtar
MASTER_SITES=	${MASTER_SITE_GITHUB:=KhronosGroup/}
GITHUB_PROJECT=	Vulkan-Utility-Libraries
GITHUB_TAG=	vulkan-sdk-${PKGVERSION_NOREV}
WRKSRC=		${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/KhronosGroup/Vulkan-Utility-Libraries/
COMMENT=	Vulkan utility headers and support libraries
LICENSE=	apache-2.0

USE_LANGUAGES=	c++
USE_CXX_FEATURES+=	c++17
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DVUL_CODEGEN=OFF
CMAKE_CONFIGURE_ARGS+=	-DUPDATE_DEPS=OFF
CMAKE_CONFIGURE_ARGS+=	-DVUL_ENABLE_INSTALL=ON

INSTALLATION_DIRS+=	share/licenses/vulkan-utility-libraries

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE.md \
	    ${DESTDIR}${PREFIX}/share/licenses/vulkan-utility-libraries/LICENSE.md
	${INSTALL_DATA} ${WRKSRC}/LICENSES/Apache-2.0.txt \
	    ${DESTDIR}${PREFIX}/share/licenses/vulkan-utility-libraries/Apache-2.0.txt
	${INSTALL_DATA} ${WRKSRC}/LICENSES/CC-BY-4.0.txt \
	    ${DESTDIR}${PREFIX}/share/licenses/vulkan-utility-libraries/CC-BY-4.0.txt

.include "../../graphics/vulkan-headers/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
