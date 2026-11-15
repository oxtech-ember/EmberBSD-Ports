BUILDLINK_TREE+= xapp
.if !defined(XAPP_BUILDLINK3_MK)
XAPP_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.xapp+= xapp>=3.4.0
BUILDLINK_PKGSRCDIR.xapp?= ../../x11/xapp
.include "../../x11/gtk3/buildlink3.mk"
.endif
BUILDLINK_TREE+= -xapp
