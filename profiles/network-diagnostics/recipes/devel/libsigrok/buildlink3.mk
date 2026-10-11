# $NetBSD$

BUILDLINK_TREE+=	libsigrok

.if !defined(LIBSIGROK_BUILDLINK3_MK)
LIBSIGROK_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.libsigrok+=	libsigrok>=0.5.0
BUILDLINK_PKGSRCDIR.libsigrok?=	../../devel/libsigrok

.include "../../archivers/libzip/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.endif	# LIBSIGROK_BUILDLINK3_MK

BUILDLINK_TREE+=	-libsigrok
