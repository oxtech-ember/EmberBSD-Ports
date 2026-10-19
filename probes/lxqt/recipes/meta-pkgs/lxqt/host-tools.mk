# Native generators for the common Qt6 LXQt cross profile.
# The caller provides the existing Qt6 host tools and LXQt CMake modules.
.include "../../meta-pkgs/lxqt/host-modules.mk"
.if !defined(EMBERBSD_QT_HOST_PATH) || !exists(${EMBERBSD_QT_HOST_PATH}/bin/lrelease)
PKG_FAIL_REASON+= "Set EMBERBSD_QT_HOST_PATH to matching Qt6 host tools with lrelease"
.endif
CMAKE_CONFIGURE_ARGS+= -DQt6LinguistTools_DIR=${EMBERBSD_QT_HOST_PATH}/lib/cmake/Qt6LinguistTools
