# $NetBSD: Makefile,v 1.10 2026/09/01 19:31:20 ktnb Exp $

DISTNAME=	litehtml-0.10
PKGREVISION=	2
CATEGORIES=	www
MASTER_SITES=	${MASTER_SITE_GITHUB:=litehtml/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.litehtml.com/
COMMENT=	Fast and lightweight HTML/CSS rendering engine
LICENSE=	modified-bsd

USE_LANGUAGES=		c c++
USE_CC_FEATURES=	c99
USE_CXX_FEATURES=	c++17

CMAKE_CONFIGURE_ARGS+=	-DEXTERNAL_GUMBO=ON
# Upstream tests are a separately pinned project; run them outside installation.
CMAKE_CONFIGURE_ARGS+=	-DLITEHTML_BUILD_TESTING:BOOL=OFF

CMAKE_USE_GNU_INSTALL_DIRS=	no

INSTALLATION_DIRS+=	share/doc/${PKGBASE}

# conform with the BSD license when distributing
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE \
		${DESTDIR}${PREFIX}/share/doc/${PKGBASE}
	${INSTALL_DATA} ${WRKSRC}/README.md \
		${DESTDIR}${PREFIX}/share/doc/${PKGBASE}

.include "../../devel/cmake/build.mk"
.include "../../www/gumbo-parser/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
