# $NetBSD$

BUILDLINK_TREE+=	aravis

.if !defined(ARAVIS_BUILDLINK3_MK)
ARAVIS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.aravis+=	aravis>=0.8.36
BUILDLINK_PKGSRCDIR.aravis?=	../../multimedia/aravis

.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/libusb1/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.endif	# ARAVIS_BUILDLINK3_MK

BUILDLINK_TREE+=	-aravis
