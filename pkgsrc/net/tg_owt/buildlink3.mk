BUILDLINK_TREE+= tg_owt
.if !defined(TG_OWT_BUILDLINK3_MK)
TG_OWT_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.tg_owt+= tg_owt>=0.0.20261030
BUILDLINK_PKGSRCDIR.tg_owt?= ../../net/tg_owt
.include "../../devel/abseil/buildlink3.mk"
.include "../../devel/crc32c/buildlink3.mk"
.include "../../multimedia/libyuv/buildlink3.mk"
.endif
BUILDLINK_TREE+= -tg_owt
