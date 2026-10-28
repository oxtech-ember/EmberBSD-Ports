# $NetBSD$
BUILDLINK_TREE+= hdr-histogram
.if !defined(HDR_HISTOGRAM_BUILDLINK3_MK)
HDR_HISTOGRAM_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.hdr-histogram+= hdr-histogram>=0.12.1
BUILDLINK_PKGSRCDIR.hdr-histogram?= ../../devel/hdr-histogram
.include "../../devel/zlib/buildlink3.mk"
.endif
BUILDLINK_TREE+= -hdr-histogram
