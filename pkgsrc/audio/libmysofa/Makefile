# $NetBSD: Makefile,v 1.13 2026/07/21 09:54:50 adam Exp $

DISTNAME=	libmysofa-1.3.5
PKGREVISION=	2
CATEGORIES=	audio
MASTER_SITES=	${MASTER_SITE_GITHUB:=hoene/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/hoene/libmysofa
COMMENT=	Reader for AES SOFA HRTF files
LICENSE=	modified-bsd


USE_LANGUAGES+=	c c++
USE_TOOLS+=	pkg-config

CMAKE_CONFIGURE_ARGS+=	-Wno-dev
.include "options.mk"

PKGCONFIG_OVERRIDE+=	libmysofa.pc.cmake

INSTALLATION_DIRS+= share/licenses/libmysofa
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/libmysofa/LICENSE
.include "../../devel/cmake/build.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
