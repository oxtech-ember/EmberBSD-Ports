# $NetBSD$
BUILDLINK_TREE+= lvgl
.if !defined(LVGL_BUILDLINK3_MK)
LVGL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.lvgl+= lvgl>=9.6.0
BUILDLINK_PKGSRCDIR.lvgl?= ../../graphics/lvgl
.endif
BUILDLINK_TREE+= -lvgl
