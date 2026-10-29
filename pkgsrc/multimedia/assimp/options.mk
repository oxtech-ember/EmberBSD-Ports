# $NetBSD: options.mk,v 1.1 2025/05/26 15:37:19 nia Exp $

PKG_OPTIONS_VAR=		PKG_OPTIONS.assimp
PKG_SUPPORTED_OPTIONS=		tests

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mtests)
CMAKE_CONFIGURE_ARGS+=	-DASSIMP_BUILD_TESTS=ON
BUILDLINK_DEPMETHOD.googletest=	build
.include "../../devel/googletest/buildlink3.mk"
.else
CMAKE_CONFIGURE_ARGS+=	-DASSIMP_BUILD_TESTS=OFF
.endif
