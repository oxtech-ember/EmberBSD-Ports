# $NetBSD$
BUILDLINK_TREE+=	delaunator
.if !defined(DELAUNATOR_BUILDLINK3_MK)
DELAUNATOR_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.delaunator+=	delaunator>=1.0.0
BUILDLINK_PKGSRCDIR.delaunator?=	../../math/delaunator
.endif
BUILDLINK_TREE+=	-delaunator
