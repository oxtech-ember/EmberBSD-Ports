# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross builds take the Linguist and Tools
# CMake packages from the native qt6-qttools package (option host-tools)
# installed in TOOLBASE.
.if !defined(QT6_QTTOOLS_HOST_TOOLS_MK)
QT6_QTTOOLS_HOST_TOOLS_MK:=
.include "../../x11/qt6-qtbase/host-tools.mk"
TOOL_DEPENDS+=	qt6-qttools>=6.12.0nb6:../../devel/qt6-qttools
CMAKE_CONFIGURE_ARGS+=	-DQt6LinguistTools_DIR:PATH=${TOOLBASE}/qt6/lib/cmake/Qt6LinguistTools
CMAKE_CONFIGURE_ARGS+=	-DQt6ToolsTools_DIR:PATH=${TOOLBASE}/qt6/lib/cmake/Qt6ToolsTools
.endif
