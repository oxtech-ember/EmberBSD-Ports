# $NetBSD$

BUILDLINK_TREE+=	glycin

.if !defined(GLYCIN_BUILDLINK3_MK)
GLYCIN_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.glycin+=	glycin>=2.0.8
BUILDLINK_PKGSRCDIR.glycin?=	../../graphics/glycin

.include "../../devel/glib2/buildlink3.mk"
.include "../../graphics/lcms2/buildlink3.mk"
.include "../../fonts/fontconfig/buildlink3.mk"
.endif	# GLYCIN_BUILDLINK3_MK

BUILDLINK_TREE+=	-glycin
