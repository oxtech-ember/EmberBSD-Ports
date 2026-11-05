# $NetBSD$
BUILDLINK_TREE+=	rectpack2d
.if !defined(RECTPACK2D_BUILDLINK3_MK)
RECTPACK2D_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.rectpack2d+=	rectpack2d>=0.0.20260810
BUILDLINK_PKGSRCDIR.rectpack2d?=	../../math/rectpack2d
.endif
BUILDLINK_TREE+=	-rectpack2d
