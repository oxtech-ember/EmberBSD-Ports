# $NetBSD: options.mk,v 1.3 2026/02/16 13:10:34 wiz Exp $

PKG_OPTIONS_VAR=		PKG_OPTIONS.zint
PKG_SUPPORTED_OPTIONS=		qt6
PKG_SUGGESTED_OPTIONS+=		qt6

PLIST_VARS+=	qt

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mqt6)
PLIST.qt=		yes
PRINT_PLIST_AWK+=	/bin\/zint-qt/ { $$0 = "$${PLIST.qt}"$$0 }
PRINT_PLIST_AWK+=	/include\/qzint.h/ { $$0 = "$${PLIST.qt}"$$0 }
PRINT_PLIST_AWK+=	/lib\/libQZint.a/ { $$0 = "$${PLIST.qt}"$$0 }
.endif

.if !empty(PKG_OPTIONS:Mqt6)
CMAKE_CONFIGURE_ARGS+=	-DZINT_USE_QT=ON
CMAKE_CONFIGURE_ARGS+=	-DZINT_QT6=ON
.include "../../graphics/qt6-qtsvg/buildlink3.mk"
.include "../../devel/qt6-qttools/buildlink3.mk"
.else
CMAKE_CONFIGURE_ARGS+=	-DZINT_USE_QT=OFF
.endif
