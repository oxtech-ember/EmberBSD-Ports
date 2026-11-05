# $NetBSD$

DISTNAME=	PEGTL-4.0.2
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=taocpp/}

MAINTAINER=	prlw1@cam.ac.uk
HOMEPAGE=	https://github.com/taocpp/PEGTL/
COMMENT=	C++ header-only parser combinator library
LICENSE=	boost-license

USE_LANGUAGES=	c++17
USE_CMAKE=	yes

CMAKE_CONFIGURE_ARGS+=	-DPEGTL_BUILD_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DPEGTL_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DPEGTL_INSTALL_CMAKE_DIR=lib/cmake/pegtl

.include "../../mk/bsd.pkg.mk"
