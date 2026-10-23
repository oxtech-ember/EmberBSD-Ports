# $NetBSD$

BUILDLINK_TREE+=	networkmanager-qt

.if !defined(NETWORKMANAGER_QT_BUILDLINK3_MK)
NETWORKMANAGER_QT_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.networkmanager-qt+=	networkmanager-qt>=6.31.0
BUILDLINK_PKGSRCDIR.networkmanager-qt?=	../../net/networkmanager-qt

.include "../../net/networkmanager-headers/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif # NETWORKMANAGER_QT_BUILDLINK3_MK

BUILDLINK_TREE+=	-networkmanager-qt
