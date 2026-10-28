# $NetBSD$
BUILDLINK_TREE+= temporal-capi
.if !defined(TEMPORAL_CAPI_BUILDLINK3_MK)
TEMPORAL_CAPI_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.temporal-capi+= temporal-capi>=0.2.6
BUILDLINK_PKGSRCDIR.temporal-capi?= ../../devel/temporal-capi
.endif
BUILDLINK_TREE+= -temporal-capi
