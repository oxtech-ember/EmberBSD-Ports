# Origin: EmberBSD (AI-assisted).
BUILDLINK_TREE+= stb-image
.if !defined(STB_IMAGE_BUILDLINK3_MK)
STB_IMAGE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.stb-image+= stb-image>=2.30.20261023
BUILDLINK_PKGSRCDIR.stb-image?= ../../graphics/stb-image
.endif
BUILDLINK_TREE+= -stb-image
