BUILDLINK_TREE+= tinyexr
.if !defined(TINYEXR_BUILDLINK3_MK)
TINYEXR_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.tinyexr+= tinyexr>=3.2.0
BUILDLINK_PKGSRCDIR.tinyexr?= ../../graphics/tinyexr
.include "../../archivers/zstd/buildlink3.mk"
.include "../../devel/libdeflate/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.endif
BUILDLINK_TREE+= -tinyexr
