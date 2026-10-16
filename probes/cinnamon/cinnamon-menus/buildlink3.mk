BUILDLINK_TREE+=	cinnamon-menus

.if !defined(CINNAMON_MENUS_BUILDLINK3_MK)
CINNAMON_MENUS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.cinnamon-menus+=	cinnamon-menus>=4.8
BUILDLINK_PKGSRCDIR.cinnamon-menus?=	../../x11/cinnamon-menus

.endif # CINNAMON_MENUS_BUILDLINK3_MK

BUILDLINK_TREE+=	-cinnamon-menus
