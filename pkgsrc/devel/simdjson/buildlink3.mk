# $NetBSD$
BUILDLINK_TREE+= simdjson
.if !defined(SIMDJSON_BUILDLINK3_MK)
SIMDJSON_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.simdjson+= simdjson>=5.0.4
BUILDLINK_PKGSRCDIR.simdjson?= ../../devel/simdjson
.endif
BUILDLINK_TREE+= -simdjson
