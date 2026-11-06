# $NetBSD: Makefile,v 1.18 2026/04/13 13:15:39 kikadf Exp $

.include "Makefile.common"

# These components use the current Vulkan SDK; other family recipes keep their pins.
SDK_VERSION=	1.4.363.0

DISTNAME=	vulkan-headers-${SDK_VERSION}
CATEGORIES=	graphics
GITHUB_PROJECT=	Vulkan-Headers
EXTRACT_USING=	bsdtar

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/KhronosGroup/Vulkan-Headers
COMMENT=	Headers for Vulkan Graphics API
LICENSE=	apache-2.0

WRKSRC=		${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}

REPLACE_PYTHON+=	registry/*.py
REPLACE_PYTHON+=	registry/spec_tools/*.py

.include "../../mk/bsd.prefs.mk"

PKG_OPTIONS_VAR=	PKG_OPTIONS.vulkan-headers
PKG_SUPPORTED_OPTIONS=	headless tests
.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mtests)
CMAKE_CONFIGURE_ARGS+=	-DVULKAN_HEADERS_ENABLE_TESTS=ON
.else
CMAKE_CONFIGURE_ARGS+=	-DVULKAN_HEADERS_ENABLE_TESTS=OFF
.endif


.include "../../devel/cmake/build.mk"
.include "../../lang/python/application.mk"
.if ${OPSYS} != "Darwin" && empty(PKG_OPTIONS:Mheadless)
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.endif
.include "../../mk/bsd.pkg.mk"
