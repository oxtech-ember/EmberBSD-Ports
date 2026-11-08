# $NetBSD$
BUILDLINK_TREE+=	sundown
.if !defined(SUNDOWN_BUILDLINK3_MK)
SUNDOWN_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.sundown+=	sundown>=1.16.0.20261029
BUILDLINK_PKGSRCDIR.sundown?=	../../textproc/sundown
.endif
BUILDLINK_TREE+=	-sundown
