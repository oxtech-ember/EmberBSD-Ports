# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). qsb executes on the host during cross builds.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && !defined(QT6_QTSHADERTOOLS_HOST_TOOLS_MK)
QT6_QTSHADERTOOLS_HOST_TOOLS_MK:=
.include "../../x11/qt6-qtbase/host-tools.mk"
TOOL_DEPENDS+=	qt6-qtshadertools>=6.12.0nb2:../../graphics/qt6-qtshadertools
CMAKE_CONFIGURE_ARGS+=	-DQt6ShaderToolsTools_DIR:PATH=${TOOLBASE}/qt6/lib/cmake/Qt6ShaderToolsTools
.endif
