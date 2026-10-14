# $NetBSD$

BUILDLINK_TREE+=	libadwaita

.if !defined(LIBADWAITA_BUILDLINK3_MK)
LIBADWAITA_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.libadwaita+=	libadwaita>=1.6
BUILDLINK_PKGSRCDIR.libadwaita?=	../../x11/libadwaita

.include "../../devel/glib2/buildlink3.mk"
.include "../../x11/gtk4/buildlink3.mk"
.endif	# LIBADWAITA_BUILDLINK3_MK

BUILDLINK_TREE+=	-libadwaita
