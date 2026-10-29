# $NetBSD$
BUILDLINK_TREE+= libspng
.if !defined(LIBSPNG_BUILDLINK3_MK)
LIBSPNG_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.libspng+= libspng>=0.7.4
BUILDLINK_PKGSRCDIR.libspng?= ../../graphics/libspng
.include "../../devel/zlib/buildlink3.mk"
.endif
BUILDLINK_TREE+= -libspng
