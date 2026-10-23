# $NetBSD: buildlink3.mk,v 1.11 2026/09/02 19:01:30 wiz Exp $

BUILDLINK_TREE+=	kf6-kcoreaddons

.if !defined(KF6_KCOREADDONS_BUILDLINK3_MK)
KF6_KCOREADDONS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kf6-kcoreaddons+=	kf6-kcoreaddons>=6.31.0
BUILDLINK_ABI_DEPENDS.kf6-kcoreaddons+=	kf6-kcoreaddons>=6.31.0nb1
BUILDLINK_PKGSRCDIR.kf6-kcoreaddons?=	../../devel/kf6-kcoreaddons
# Cross KDE builds name these files relative to the buildlink prefix.
BUILDLINK_FILES.kf6-kcoreaddons+=	qt6/metatypes/qt6kf6coreaddons_metatypes.json

.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif	# KF6_KCOREADDONS_BUILDLINK3_MK

BUILDLINK_TREE+=	-kf6-kcoreaddons
