# $NetBSD$

DISTNAME=	json-schema-validator-2.4.1
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=pboettch/}
GITHUB_TAG=	${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/pboettch/json-schema-validator
COMMENT=	JSON Schema validator for nlohmann/json
LICENSE=	mit

USE_LANGUAGES=	c++
CMAKE_CONFIGURE_ARGS+=	-DJSON_VALIDATOR_INSTALL=ON
CMAKE_CONFIGURE_ARGS+=	-DJSON_VALIDATOR_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DJSON_VALIDATOR_BUILD_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DJSON_VALIDATOR_SHARED_LIBS=ON

INSTALLATION_DIRS+=	share/licenses/json-schema-validator
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/json-schema-validator/LICENSE

BUILDLINK_API_DEPENDS.nlohmann-json+=	nlohmann-json>=3.12.0
.include "../../textproc/nlohmann-json/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
