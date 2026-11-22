# $NetBSD: buildlink3.mk,v 1.28 2026/09/02 19:01:35 wiz Exp $

BUILDLINK_TREE+=	libadwaita

.if !defined(LIBADWAITA_BUILDLINK3_MK)
LIBADWAITA_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.libadwaita+=	libadwaita>=1.0.5
BUILDLINK_ABI_DEPENDS.libadwaita+=	libadwaita>=1.9.1nb1
BUILDLINK_PKGSRCDIR.libadwaita?=	../../devel/libadwaita

.include "../../converters/fribidi/buildlink3.mk"
.include "../../devel/ministream/buildlink3.mk"
BUILDLINK_API_DEPENDS.glib2+=	glib2>=2.89.3
.include "../../devel/glib2/buildlink3.mk"
BUILDLINK_API_DEPENDS.gtk4+=	gtk4>=4.23.1
.include "../../x11/gtk4/buildlink3.mk"
.endif	# LIBADWAITA_BUILDLINK3_MK

BUILDLINK_TREE+=	-libadwaita
