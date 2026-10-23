# $NetBSD: buildlink3.mk,v 1.13 2026/09/02 19:05:14 wiz Exp $

BUILDLINK_TREE+=	kf6-kwindowsystem

.if !defined(KF6_KWINDOWSYSTEM_BUILDLINK3_MK)
KF6_KWINDOWSYSTEM_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kf6-kwindowsystem+=	kf6-kwindowsystem>=6.31.0nb1
BUILDLINK_ABI_DEPENDS.kf6-kwindowsystem+=	kf6-kwindowsystem>=6.31.0nb1
BUILDLINK_PKGSRCDIR.kf6-kwindowsystem?=		../../x11/kf6-kwindowsystem

USE_CXX_FEATURES+=	c++20

# Qt 6.12 exports WaylandClient from Qtbase.
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif	# KF6_KWINDOWSYSTEM_BUILDLINK3_MK

BUILDLINK_TREE+=	-kf6-kwindowsystem
