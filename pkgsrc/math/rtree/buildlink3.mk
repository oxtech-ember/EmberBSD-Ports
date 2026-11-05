# $NetBSD$
BUILDLINK_TREE+=	rtree
.if !defined(RTREE_BUILDLINK3_MK)
RTREE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.rtree+=	rtree>=10.0.8
BUILDLINK_PKGSRCDIR.rtree?=	../../math/rtree
.endif
BUILDLINK_TREE+=	-rtree
