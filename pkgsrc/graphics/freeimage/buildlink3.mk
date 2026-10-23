# Origin: EmberBSD, canonical maintained FreeImage ABI3.
BUILDLINK_TREE+=	freeimage
.if !defined(FREEIMAGE_BUILDLINK3_MK)
FREEIMAGE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.freeimage+=	freeimage>=3.19.25
BUILDLINK_PKGSRCDIR.freeimage?=	../../graphics/freeimage
.endif
BUILDLINK_TREE+=	-freeimage
