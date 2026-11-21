# $NetBSD: Makefile,v 1.12 2026/04/13 13:19:10 kikadf Exp $

# Origin: EmberBSD contributors (AI-assisted); independent stable header release.
DISTNAME=	SPIRV-Headers-1.4.363.0
PKGNAME=	${DISTNAME:tl}
PKGREVISION=	2
CATEGORIES=	parallel
MASTER_SITES=	${MASTER_SITE_GITHUB:=KhronosGroup/}
GITHUB_PROJECT=	SPIRV-Headers
GITHUB_TAG=	vulkan-sdk-${PKGVERSION_NOREV}
# SPIRV-LLVM-Translator 23.1.3 uses the subgroup bitcast shuffle extension.
PATCH_SITES=	https://github.com/KhronosGroup/SPIRV-Headers/commit/
PATCHFILES=	cb42dec3830d3ac67fa449ecdc0c0f73d5e74498.patch
PATCH_DIST_STRIP= -p1
USE_LANGUAGES=	c c++
USE_TOOLS+=	find

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/KhronosGroup/SPIRV-Headers
COMMENT=	Headers for translation between SPIR-V and LLVM IR
LICENSE=	mit

WRKSRC=		${WRKDIR}/SPIRV-Headers-${GITHUB_TAG}

PKG_OPTIONS_VAR= PKG_OPTIONS.spirv-headers
PKG_SUPPORTED_OPTIONS+= tests
.include "../../mk/bsd.options.mk"
.if !empty(PKG_OPTIONS:Mtests)
CMAKE_CONFIGURE_ARGS+= -DSPIRV_HEADERS_ENABLE_TESTS=ON
.else
CMAKE_CONFIGURE_ARGS+= -DSPIRV_HEADERS_ENABLE_TESTS=OFF
.endif

PKGCONFIG_OVERRIDE+=	SPIRV-Headers.pc.in

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/spirv-headers
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/spirv-headers/LICENSE

pre-configure:
	${FIND} ${WRKSRC}/include/spirv/unified1 -type f -name '*.orig*' -exec ${RM} -f {} +

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
