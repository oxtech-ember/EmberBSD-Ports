# Native LXQt CMake modules. Data generators do not require target Qt.
CMAKE_CONFIGURE_ARGS+= -DLXQT_ETC_XDG_DIR=${PKG_SYSCONFBASE}/xdg
.if defined(EMBERBSD_LXQT_HOST_TOOLS)
.if !exists(${EMBERBSD_LXQT_HOST_TOOLS}/share/cmake/lxqt2-build-tools/lxqt2-build-tools-config.cmake)
PKG_FAIL_REASON+= "The selected LXQt host prefix lacks lxqt2-build-tools"
.endif
CMAKE_CONFIGURE_ARGS+= -Dlxqt2-build-tools_DIR=${EMBERBSD_LXQT_HOST_TOOLS}/share/cmake/lxqt2-build-tools
.else
TOOL_DEPENDS+= lxqt-build-tools>=2.5.0nb2:../../devel/lxqt-build-tools
CMAKE_CONFIGURE_ARGS+= -Dlxqt2-build-tools_DIR=${TOOLBASE}/share/cmake/lxqt2-build-tools
.endif
