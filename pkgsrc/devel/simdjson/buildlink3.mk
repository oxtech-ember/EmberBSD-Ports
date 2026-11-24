# $NetBSD$
BUILDLINK_TREE+= simdjson
.if !defined(SIMDJSON_BUILDLINK3_MK)
SIMDJSON_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.simdjson+= simdjson>=5.0.6
BUILDLINK_ABI_DEPENDS.simdjson+= simdjson>=5.3.0
BUILDLINK_PKGSRCDIR.simdjson?= ../../devel/simdjson
.endif
BUILDLINK_TREE+= -simdjson
