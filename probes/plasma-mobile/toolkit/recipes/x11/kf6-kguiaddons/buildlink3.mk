# $NetBSD: buildlink3.mk,v 1.11 2026/09/02 19:05:13 wiz Exp $

BUILDLINK_TREE+=	kf6-kguiaddons

.if !defined(KF6_KGUIADDONS_BUILDLINK3_MK)
KF6_KGUIADDONS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kf6-kguiaddons+=	kf6-kguiaddons>=6.31.0
BUILDLINK_ABI_DEPENDS.kf6-kguiaddons+=	kf6-kguiaddons>=6.31.0
BUILDLINK_PKGSRCDIR.kf6-kguiaddons?=	../../x11/kf6-kguiaddons

# Qt 6.12 exports WaylandClient from Qtbase.
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif	# KF6_KGUIADDONS_BUILDLINK3_MK

BUILDLINK_TREE+=	-kf6-kguiaddons
