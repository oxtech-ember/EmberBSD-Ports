# $NetBSD: Makefile,v 1.16 2024/11/23 10:11:58 mef Exp $

DISTNAME=	kicad-symbols-10.0.7
CATEGORIES=	cad
MASTER_SITES=	${MASTER_SITE_GITLAB:=kicad/libraries/}
GITLAB_RELEASE=	${PKGVERSION_NOREV}
EXTRACT_SUFX=	.tar.bz2

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.kicad.org/
COMMENT=	Schematic symbol libraries for the schematic CAD software
LICENSE=	cc-by-sa-v4.0

USE_LANGUAGES=	# none

# Origin: EmberBSD contributors (AI-assisted). Keep the upstream license exception.
INSTALLATION_DIRS+=	share/doc/${PKGBASE}

PYTHON_FOR_BUILD_ONLY=	tool
CMAKE_CONFIGURE_ARGS+=	-DPython3_EXECUTABLE:FILEPATH=${TOOL_PYTHONBIN}
CMAKE_CONFIGURE_ARGS+=	-DKICAD_PACK_SYM_LIBRARIES=ON

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE.md ${DESTDIR}${PREFIX}/share/doc/${PKGBASE}/LICENSE.md

.include "../../devel/cmake/build.mk"
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
