# $NetBSD$

BUILDLINK_TREE+=	qt6-qtgraphs

.if !defined(QT6_QTGRAPHS_BUILDLINK3_MK)
QT6_QTGRAPHS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.qt6-qtgraphs+=	qt6-qtgraphs>=6.12.0
BUILDLINK_ABI_DEPENDS.qt6-qtgraphs+=	qt6-qtgraphs>=6.12.0
BUILDLINK_PKGSRCDIR.qt6-qtgraphs?=	../../graphics/qt6-qtgraphs

.include "../../graphics/qt6-qtquick3d/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif	# QT6_QTGRAPHS_BUILDLINK3_MK

BUILDLINK_TREE+=	-qt6-qtgraphs
