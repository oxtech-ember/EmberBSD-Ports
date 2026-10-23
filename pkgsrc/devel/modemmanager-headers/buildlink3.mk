# $NetBSD$

BUILDLINK_TREE+=	modemmanager-headers

.if !defined(MODEMMANAGER_HEADERS_BUILDLINK3_MK)
MODEMMANAGER_HEADERS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.modemmanager-headers+=	modemmanager-headers>=1.22
BUILDLINK_PKGSRCDIR.modemmanager-headers?=	../../devel/modemmanager-headers
.endif # MODEMMANAGER_HEADERS_BUILDLINK3_MK

BUILDLINK_TREE+=	-modemmanager-headers
