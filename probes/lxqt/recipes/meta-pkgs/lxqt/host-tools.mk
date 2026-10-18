# Native generators for the common Qt6 LXQt cross profile.
# The caller provides the existing Qt6 host tools and LXQt CMake modules.
.if !defined(EMBERBSD_LXQT_HOST_TOOLS) || !exists(${EMBERBSD_LXQT_HOST_TOOLS}/share/cmake/lxqt2-build-tools/lxqt2-build-tools-config.cmake)
PKG_FAIL_REASON+= "Set EMBERBSD_LXQT_HOST_TOOLS to the prepared LXQt 2.4 host prefix"
.endif
.if !defined(EMBERBSD_QT_HOST_PATH) || !exists(${EMBERBSD_QT_HOST_PATH}/bin/lrelease)
PKG_FAIL_REASON+= "Set EMBERBSD_QT_HOST_PATH to matching Qt6 host tools with lrelease"
.endif
CMAKE_CONFIGURE_ARGS+= -Dlxqt2-build-tools_DIR=${EMBERBSD_LXQT_HOST_TOOLS}/share/cmake/lxqt2-build-tools
CMAKE_CONFIGURE_ARGS+= -DQt6LinguistTools_DIR=${EMBERBSD_QT_HOST_PATH}/lib/cmake/Qt6LinguistTools
