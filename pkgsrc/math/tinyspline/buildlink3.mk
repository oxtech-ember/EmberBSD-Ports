# $NetBSD$
BUILDLINK_TREE+=	tinyspline
.if !defined(TINYSPLINE_BUILDLINK3_MK)
TINYSPLINE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.tinyspline+=	tinyspline>=0.6.0
BUILDLINK_PKGSRCDIR.tinyspline?=	../../math/tinyspline
.endif
BUILDLINK_TREE+=	-tinyspline
