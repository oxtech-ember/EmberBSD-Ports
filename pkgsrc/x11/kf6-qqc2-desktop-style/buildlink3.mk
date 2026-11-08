# $NetBSD$

BUILDLINK_TREE+=	kf6-qqc2-desktop-style

.if !defined(KF6_QQC2_DESKTOP_STYLE_BUILDLINK3_MK)
KF6_QQC2_DESKTOP_STYLE_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kf6-qqc2-desktop-style+=	kf6-qqc2-desktop-style>=6.31.0
BUILDLINK_PKGSRCDIR.kf6-qqc2-desktop-style?=	../../x11/kf6-qqc2-desktop-style

.endif	# KF6_QQC2_DESKTOP_STYLE_BUILDLINK3_MK

BUILDLINK_TREE+=	-kf6-qqc2-desktop-style
