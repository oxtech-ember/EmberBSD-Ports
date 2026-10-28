# $NetBSD: Makefile,v 1.3 2024/08/25 06:18:38 wiz Exp $

DISTNAME=	tl-expected-1.3.1
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=TartanLlama/}
GITHUB_PROJECT=	expected
GITHUB_TAG=	v${PKGVERSION_NOREV}
WRKSRC= ${WRKDIR}/expected-${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/TartanLlama/expected
COMMENT=	C++11/14/17 std::expected with functional-style extensions
LICENSE=	cc0-1.0-universal


USE_LANGUAGES=	c c++

# The upstream pkgsrc recipe disabled its test build; preserve this default.
CMAKE_CONFIGURE_ARGS+= -DEXPECTED_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+= -DEXPECTED_BUILD_PACKAGE=OFF

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
