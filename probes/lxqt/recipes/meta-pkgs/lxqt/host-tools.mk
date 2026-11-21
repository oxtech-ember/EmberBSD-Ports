# Native generators for the common Qt6 LXQt cross profile.
.include "../../meta-pkgs/lxqt/host-modules.mk"
.if defined(EMBERBSD_QT_HOST_PATH)
.if !exists(${EMBERBSD_QT_HOST_PATH}/bin/lrelease)
PKG_FAIL_REASON+= "The selected Qt host prefix lacks lrelease"
.endif
CMAKE_CONFIGURE_ARGS+= -DQt6LinguistTools_DIR=${EMBERBSD_QT_HOST_PATH}/lib/cmake/Qt6LinguistTools
.else
.include "../../devel/qt6-qttools/host-tools.mk"
.endif
