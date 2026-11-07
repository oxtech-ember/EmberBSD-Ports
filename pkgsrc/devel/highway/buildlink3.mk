# $NetBSD$

BUILDLINK_TREE+=	highway

.if !defined(HIGHWAY_BUILDLINK3_MK)
HIGHWAY_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.highway+=	highway>=1.3.0
BUILDLINK_PKGSRCDIR.highway?=	../../devel/highway
.endif

BUILDLINK_TREE+=	-highway
