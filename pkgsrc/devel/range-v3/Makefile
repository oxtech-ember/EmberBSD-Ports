# $NetBSD: Makefile,v 1.3 2024/08/25 06:18:37 wiz Exp $

DISTNAME=	range-v3-0.12.0
PKGREVISION= 1
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=ericniebler/}
DISTFILES=	range-v3-0.12.0.tar.gz
SITES.range-v3-0.12.0.tar.gz= -https://github.com/ericniebler/range-v3/archive/refs/tags/0.12.0.tar.gz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/ericniebler/range-v3
COMMENT=	Range library for C++14/17/20, basis for std::ranges in C++20
LICENSE=	boost-license

USE_LANGUAGES=	c c++

CMAKE_CONFIGURE_ARGS+=	-DRANGES_NATIVE=OFF
CMAKE_CONFIGURE_ARGS+=	-DRANGES_BUILD_CALENDAR_EXAMPLE=OFF

CMAKE_CONFIGURE_ARGS+=	-DRANGE_V3_DOCS=OFF
CMAKE_CONFIGURE_ARGS+=	-DRANGE_V3_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DRANGE_V3_HEADER_CHECKS=OFF
CMAKE_CONFIGURE_ARGS+=	-DRANGE_V3_TESTS=OFF

INSTALLATION_DIRS+= share/licenses/range-v3
post-install:
	${RM} -f ${DESTDIR}${PREFIX}/include/module.modulemap
	${INSTALL_DATA} ${WRKSRC}/LICENSE.txt ${DESTDIR}${PREFIX}/share/licenses/range-v3/LICENSE.txt

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
