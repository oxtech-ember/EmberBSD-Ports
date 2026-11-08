# $NetBSD$

BUILDLINK_TREE+=	callaudiod

.if !defined(CALLAUDIOD_BUILDLINK3_MK)
CALLAUDIOD_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.callaudiod+=	callaudiod>=0.1.4
BUILDLINK_PKGSRCDIR.callaudiod?=	../../audio/callaudiod

.include "../../devel/glib2/buildlink3.mk"
.endif	# CALLAUDIOD_BUILDLINK3_MK

BUILDLINK_TREE+=	-callaudiod
