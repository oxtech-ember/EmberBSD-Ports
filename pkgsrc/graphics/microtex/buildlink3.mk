# $NetBSD$
BUILDLINK_TREE+= microtex
.if !defined(MICROTEX_BUILDLINK3_MK)
MICROTEX_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.microtex+= microtex>=0.0.20260814
BUILDLINK_PKGSRCDIR.microtex?= ../../graphics/microtex
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif
BUILDLINK_TREE+= -microtex
