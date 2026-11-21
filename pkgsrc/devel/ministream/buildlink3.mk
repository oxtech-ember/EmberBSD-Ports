# $NetBSD$

BUILDLINK_TREE+=	ministream

.if !defined(MINISTREAM_BUILDLINK3_MK)
MINISTREAM_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.ministream+=	ministream>=0.99.1
BUILDLINK_PKGSRCDIR.ministream?=	../../devel/ministream

.include "../../devel/glib2/buildlink3.mk"
.endif	# MINISTREAM_BUILDLINK3_MK

BUILDLINK_TREE+=	-ministream
