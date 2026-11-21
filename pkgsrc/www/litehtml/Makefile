# $NetBSD$

DISTNAME=	twidget
PKGNAME=	litehtml-0.10
PKGREVISION=	3
CATEGORIES=	www
MASTER_SITES=	${MASTER_SITE_GITHUB:=TelegramMessenger/}
GITHUB_PROJECT=	twidget
GITHUB_TAG=	866f0971e7cc5cdeaa07571d9095a94a68b31c96
WRKSRC=		${WRKDIR}/twidget-${GITHUB_TAG}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/TelegramMessenger/twidget
COMMENT=	Fast and lightweight HTML/CSS rendering engine
LICENSE=	modified-bsd

USE_LANGUAGES=		c c++
USE_CC_FEATURES=	c99
USE_CXX_FEATURES=	c++17

CMAKE_CONFIGURE_ARGS+=	-DTWIDGET_LITEHTML_ONLY:BOOL=ON
BUILDLINK_API_DEPENDS.gumbo-parser+= gumbo-parser>=0.14.1nb2

.include "../../devel/cmake/build.mk"
.include "../../www/gumbo-parser/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
