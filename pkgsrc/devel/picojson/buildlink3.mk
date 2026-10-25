# Origin: EmberBSD contributors (AI-assisted).
BUILDLINK_TREE+= picojson
.if !defined(PICOJSON_BUILDLINK3_MK)
PICOJSON_BUILDLINK3_MK:=
BUILDLINK_DEPMETHOD.picojson?= build
BUILDLINK_API_DEPENDS.picojson+= picojson>=1.3.0.20210117
BUILDLINK_PKGSRCDIR.picojson?= ../../devel/picojson
.endif
BUILDLINK_TREE+= -picojson
