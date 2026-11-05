BUILDLINK_TREE+= cld3
.if !defined(CLD3_BUILDLINK3_MK)
CLD3_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.cld3+= cld3>=3.0.13
BUILDLINK_PKGSRCDIR.cld3?= ../../textproc/cld3
.include "../../devel/protobuf/buildlink3.mk"
.endif
BUILDLINK_TREE+= -cld3
