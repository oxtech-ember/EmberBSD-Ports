# $NetBSD$

BUILDLINK_TREE+=	kdeconnect-kde

.if !defined(KDECONNECT_KDE_BUILDLINK3_MK)
KDECONNECT_KDE_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kdeconnect-kde+=	kdeconnect-kde>=25.08.3
BUILDLINK_PKGSRCDIR.kdeconnect-kde?=	../../net/kdeconnect-kde

.endif	# KDECONNECT_KDE_BUILDLINK3_MK

BUILDLINK_TREE+=	-kdeconnect-kde
