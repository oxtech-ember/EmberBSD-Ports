# $NetBSD$

BUILDLINK_TREE+=	modemmanager-qt

.if !defined(MODEMMANAGER_QT_BUILDLINK3_MK)
MODEMMANAGER_QT_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.modemmanager-qt+=	modemmanager-qt>=6.31.0
BUILDLINK_PKGSRCDIR.modemmanager-qt?=	../../net/modemmanager-qt

.include "../../devel/modemmanager-headers/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif # MODEMMANAGER_QT_BUILDLINK3_MK

BUILDLINK_TREE+=	-modemmanager-qt
