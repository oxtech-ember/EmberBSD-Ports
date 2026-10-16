BUILDLINK_TREE+=	cinnamon-desktop

.if !defined(CINNAMON_DESKTOP_BUILDLINK3_MK)
CINNAMON_DESKTOP_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.cinnamon-desktop+=	cinnamon-desktop>=5.3
BUILDLINK_PKGSRCDIR.cinnamon-desktop?=	../../x11/cinnamon-desktop

.endif # CINNAMON_DESKTOP_BUILDLINK3_MK

BUILDLINK_TREE+=	-cinnamon-desktop
