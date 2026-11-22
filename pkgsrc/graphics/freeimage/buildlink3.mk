# Origin: EmberBSD, canonical maintained FreeImage ABI3.
BUILDLINK_TREE+=	freeimage
.if !defined(FREEIMAGE_BUILDLINK3_MK)
FREEIMAGE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.freeimage+=	freeimage>=3.19.33
BUILDLINK_PKGSRCDIR.freeimage?=	../../graphics/freeimage

# The exported FreeImage CMake package resolves its system JPEG dependency.
.include "../../graphics/libjpeg-turbo/buildlink3.mk"
.endif
BUILDLINK_TREE+=	-freeimage
