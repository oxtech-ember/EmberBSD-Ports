# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Target SDK files are build-only dependencies.
BUILDLINK_TREE+= qt6-qtbase-devel
.if !defined(QT6_QTBASE_DEVEL_BUILDLINK3_MK)
QT6_QTBASE_DEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.qt6-qtbase-devel+= qt6-qtbase-devel>=6.12.0nb7
BUILDLINK_ABI_DEPENDS.qt6-qtbase-devel+= qt6-qtbase-devel>=6.12.0nb7
BUILDLINK_PKGSRCDIR.qt6-qtbase-devel?= ../../x11/qt6-qtbase-devel
BUILDLINK_DEPMETHOD.qt6-qtbase-devel= build
BUILDLINK_INCDIRS.qt6-qtbase-devel+= qt6/include
# This package owns only SDK files. Preserve all imported CMake/qmake targets,
# including resource objects; do not hide files required by the full sysroot.
BUILDLINK_CONTENTS_FILTER.qt6-qtbase-devel= ${CAT}
.endif
BUILDLINK_TREE+= -qt6-qtbase-devel
