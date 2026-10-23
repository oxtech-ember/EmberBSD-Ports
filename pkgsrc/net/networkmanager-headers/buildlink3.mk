# $NetBSD$

BUILDLINK_TREE+=	networkmanager-headers

.if !defined(NETWORKMANAGER_HEADERS_BUILDLINK3_MK)
NETWORKMANAGER_HEADERS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.networkmanager-headers+=	networkmanager-headers>=1.52
BUILDLINK_PKGSRCDIR.networkmanager-headers?=	../../net/networkmanager-headers

.include "../../devel/glib2/buildlink3.mk"
.endif # NETWORKMANAGER_HEADERS_BUILDLINK3_MK

BUILDLINK_TREE+=	-networkmanager-headers
