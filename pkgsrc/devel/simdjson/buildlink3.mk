# $NetBSD$
BUILDLINK_TREE+= simdjson
.if !defined(SIMDJSON_BUILDLINK3_MK)
SIMDJSON_BUILDLINK3_MK:=
.include "../../mk/bsd.fast.prefs.mk"
BUILDLINK_API_DEPENDS.simdjson+= simdjson>=5.0.6
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.simdjson+= simdjson>=5.0.6nb1
.endif
BUILDLINK_PKGSRCDIR.simdjson?= ../../devel/simdjson
.endif
BUILDLINK_TREE+= -simdjson
