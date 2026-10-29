# $NetBSD: Makefile,v 1.22 2026/05/03 10:01:40 wiz Exp $

DISTNAME=	assimp-6.0.5
PKGREVISION=	1
CATEGORIES=	multimedia
MASTER_SITES=	${MASTER_SITE_GITHUB:=assimp/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.assimp.org/
COMMENT=	Library to import various 3D model formats
LICENSE=	modified-bsd

USE_CXX_FEATURES=	c++17

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+=	libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+=	EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
USE_LANGUAGES=		c c++
USE_TOOLS+=		pkg-config
PKGCONFIG_OVERRIDE=	assimp.pc.in

CMAKE_CONFIGURE_ARGS+=	-Dopen3dgc_DIR=${BUILDLINK_DIR}/lib/cmake/open3dgc
CMAKE_CONFIGURE_ARGS+=	-DASSIMP_BUILD_ZLIB=OFF
CMAKE_CONFIGURE_ARGS+=	-DASSIMP_WARNINGS_AS_ERRORS=OFF

.include "options.mk"
.include "../../devel/cmake/build.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../archivers/minizip/buildlink3.mk"
BUILDLINK_INCDIRS.minizip= include
.include "../../textproc/pugixml/buildlink3.mk"
.include "../../math/poly2tri/buildlink3.mk"
.include "../../math/open3dgc/buildlink3.mk"
.include "../../math/clipper2/buildlink3.mk"
.include "../../devel/openddl-parser/buildlink3.mk"
.include "../../textproc/rapidjson/buildlink3.mk"
.include "../../textproc/utf8-cpp/buildlink3.mk"
.include "../../graphics/stb-image/buildlink3.mk"
.include "../../archivers/libzip/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
