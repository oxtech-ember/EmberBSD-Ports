# Native LXQt CMake modules. Data generators do not require target Qt.
.if !defined(EMBERBSD_LXQT_HOST_TOOLS) || !exists(${EMBERBSD_LXQT_HOST_TOOLS}/share/cmake/lxqt2-build-tools/lxqt2-build-tools-config.cmake)
PKG_FAIL_REASON+= "Set EMBERBSD_LXQT_HOST_TOOLS to the prepared LXQt 2.4 host prefix"
.endif
CMAKE_CONFIGURE_ARGS+= -Dlxqt2-build-tools_DIR=${EMBERBSD_LXQT_HOST_TOOLS}/share/cmake/lxqt2-build-tools
