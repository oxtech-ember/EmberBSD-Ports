# $NetBSD$
BUILDLINK_TREE+= uvwasi
.if !defined(UVWASI_BUILDLINK3_MK)
UVWASI_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.uvwasi+= uvwasi>=0.0.23
BUILDLINK_ABI_DEPENDS.uvwasi+= uvwasi>=0.0.23nb1
BUILDLINK_PKGSRCDIR.uvwasi?= ../../devel/uvwasi
.include "../../devel/libuv/buildlink3.mk"
.endif
BUILDLINK_TREE+= -uvwasi
