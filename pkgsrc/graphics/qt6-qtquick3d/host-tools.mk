# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors. balsam executes on the host during cross builds.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && !defined(QT6_QTQUICK3D_HOST_TOOLS_MK)
QT6_QTQUICK3D_HOST_TOOLS_MK:=
.include "../../x11/qt6-qtbase/host-tools.mk"
TOOL_DEPENDS+=	qt6-qtquick3d>=6.12.0nb4:../../graphics/qt6-qtquick3d
CMAKE_CONFIGURE_ARGS+=	-DQt6Quick3DTools_DIR:PATH=${TOOLBASE}/qt6/lib/cmake/Qt6Quick3DTools
.endif
