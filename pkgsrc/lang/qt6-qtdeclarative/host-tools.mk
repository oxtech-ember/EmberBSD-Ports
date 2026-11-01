# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). QML generators execute on the host in cross builds.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && !defined(QT6_QTDECLARATIVE_HOST_TOOLS_MK)
QT6_QTDECLARATIVE_HOST_TOOLS_MK:=
.include "../../x11/qt6-qtbase/host-tools.mk"
TOOL_DEPENDS+=	qt6-qtdeclarative>=6.12.0nb4:../../lang/qt6-qtdeclarative
CMAKE_CONFIGURE_ARGS+=	-DQt6QmlTools_DIR:PATH=${TOOLBASE}/qt6/lib/cmake/Qt6QmlTools
CMAKE_CONFIGURE_ARGS+=	-DQt6QuickTools_DIR:PATH=${TOOLBASE}/qt6/lib/cmake/Qt6QuickTools
.endif
