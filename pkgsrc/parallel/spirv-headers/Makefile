# $NetBSD: Makefile,v 1.12 2026/04/13 13:19:10 kikadf Exp $

# Origin: EmberBSD contributors (AI-assisted); independent stable header release.
DISTNAME=	SPIRV-Headers-1.4.363.0
PKGNAME=	${DISTNAME:tl}
CATEGORIES=	parallel
MASTER_SITES=	${MASTER_SITE_GITHUB:=KhronosGroup/}
GITHUB_PROJECT=	SPIRV-Headers
GITHUB_TAG=	vulkan-sdk-${PKGVERSION_NOREV}
USE_LANGUAGES=	c c++

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/KhronosGroup/SPIRV-Headers
COMMENT=	Headers for translation between SPIR-V and LLVM IR
LICENSE=	mit

WRKSRC=		${WRKDIR}/SPIRV-Headers-${GITHUB_TAG}

PKGCONFIG_OVERRIDE+=	SPIRV-Headers.pc.in

pre-configure:
	${RM} -rf ${WRKSRC}/include/spirv/unified1/*.orig*

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
