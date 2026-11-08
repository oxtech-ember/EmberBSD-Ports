# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME=	nanodbc-3.0.8
CATEGORIES=	databases
MASTER_SITES=	${MASTER_SITE_GITHUB:=nanodbc/}
GITHUB_TAG=	v${PKGVERSION_NOREV}
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://nanodbc.github.io/nanodbc/
COMMENT=	C++ interface to ODBC database drivers
LICENSE=	mit

USE_LANGUAGES=	c++
USE_CXX_FEATURES=	c++17
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+=	-DNANODBC_FORCE_LIBCXX=OFF
CMAKE_CONFIGURE_ARGS+=	-DNANODBC_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DNANODBC_BUILD_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DNANODBC_GENERATE_INSTALL=ON
CMAKE_CONFIGURE_ARGS+=	-DNANODBC_ENABLE_UNICODE=ON
CMAKE_CONFIGURE_ARGS+=	-DNANODBC_ENABLE_BOOST=ON

post-extract:
	${CP} ${FILESDIR}/nanodbc-config.cmake.in ${WRKSRC}/

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/nanodbc
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/nanodbc/LICENSE

.include "../../databases/unixodbc/buildlink3.mk"
.include "../../devel/boost-libs/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
