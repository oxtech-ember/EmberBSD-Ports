# $NetBSD$
BUILDLINK_TREE+=	glad
.if !defined(GLAD_BUILDLINK3_MK)
GLAD_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.glad+=	glad>=2.0.8
BUILDLINK_ABI_DEPENDS.glad?=	glad>=2.0.8
BUILDLINK_PKGSRCDIR.glad?=	../../graphics/glad
BUILDLINK_DEPMETHOD.libX11?=	build
.include "../../graphics/egl-headers/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/xorgproto/buildlink3.mk"
.endif
BUILDLINK_TREE+=	-glad
