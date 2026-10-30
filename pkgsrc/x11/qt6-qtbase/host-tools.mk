# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross builds take moc, rcc and their CMake
# packages from the native qt6-qtbase package (option host-tools) in TOOLBASE.
.if !defined(QT6_QTBASE_HOST_TOOLS_MK)
QT6_QTBASE_HOST_TOOLS_MK:=
.include "../../x11/qt6-qtbase/native-runtime.mk"
TOOL_DEPENDS+=	qt6-qtbase>=6.12.0nb12:../../x11/qt6-qtbase
QT_HOST_PATH=	${TOOLBASE}/qt6
CMAKE_CONFIGURE_ARGS+=	-DQT_HOST_PATH:PATH=${QT_HOST_PATH}
.endif
