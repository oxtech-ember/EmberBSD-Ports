# $NetBSD$

PKG_OPTIONS_VAR=		PKG_OPTIONS.qt6-qtquick3d
PKG_SUPPORTED_OPTIONS=	assimp
PKG_SUGGESTED_OPTIONS=	assimp

PLIST_VARS+=		assimp

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Massimp)
PLIST.assimp=		yes
.include "../../multimedia/assimp/buildlink3.mk"
.else
# Keep the QtQuick3D runtime and spatial-audio API without model importers.
CMAKE_CONFIGURE_ARGS+=	-DFEATURE_quick3d_assimp:BOOL=OFF
.endif
