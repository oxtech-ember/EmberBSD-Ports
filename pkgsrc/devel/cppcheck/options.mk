# Origin: EmberBSD contributors (AI-assisted).
PKG_OPTIONS_VAR= PKG_OPTIONS.cppcheck
PKG_SUPPORTED_OPTIONS= qt6
PKG_OPTIONS_LEGACY_OPTS+= qt5:qt6

.include "../../mk/bsd.options.mk"

PLIST_VARS+= qt6
.if !empty(PKG_OPTIONS:Mqt6)
PLIST.qt6= yes
CMAKE_CONFIGURE_ARGS+= -DBUILD_GUI:BOOL=ON
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/qt6-qttools/buildlink3.mk"
.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../x11/qt6-qtbase/host-tools.mk"
.endif
.endif
