# $NetBSD$
BUILDLINK_TREE+=	parson
.if !defined(PARSON_BUILDLINK3_MK)
PARSON_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.parson+=	parson>=1.5.4
BUILDLINK_PKGSRCDIR.parson?=	../../textproc/parson
.endif
BUILDLINK_TREE+=	-parson
