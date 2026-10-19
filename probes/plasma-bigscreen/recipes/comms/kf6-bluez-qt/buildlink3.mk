# $NetBSD$

BUILDLINK_TREE+= kf6-bluez-qt
.if !defined(KF6_BLUEZ_QT_BUILDLINK3_MK)
KF6_BLUEZ_QT_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.kf6-bluez-qt+= kf6-bluez-qt>=6.31.0
BUILDLINK_PKGSRCDIR.kf6-bluez-qt?= ../../comms/kf6-bluez-qt
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif
BUILDLINK_TREE+= -kf6-bluez-qt
