# $NetBSD$
BUILDLINK_TREE+=	dxflib
.if !defined(DXFLIB_BUILDLINK3_MK)
DXFLIB_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.dxflib+=	dxflib>=3.26.4
BUILDLINK_PKGSRCDIR.dxflib?=	../../cad/dxflib
.endif
BUILDLINK_TREE+=	-dxflib
