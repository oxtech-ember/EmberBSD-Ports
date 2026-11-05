BUILDLINK_TREE+= libyuv
.if !defined(LIBYUV_BUILDLINK3_MK)
LIBYUV_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.libyuv+= libyuv>=0.0.1978
BUILDLINK_PKGSRCDIR.libyuv?= ../../multimedia/libyuv
.endif
BUILDLINK_TREE+= -libyuv
